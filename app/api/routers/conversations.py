from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import current_user
from app.api.dependencies.db import get_db
from app.api.schemas.conversation import (
    ChatRequest,
    ChatResponse,
    CitationRead,
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
)
from app.agent.state import AgentState
from app.core.observability import agent_run_context, log_turn_metrics, open_conversation_run
from app.db.orm.conversation import Conversation
from app.db.orm.knowledge_base import KnowledgeBase
from app.db.orm.message import Message, MessageCitation, MessageRole
from app.db.orm.user import User

router = APIRouter(prefix="/conversations", tags=["conversations"])

_CurrentUser = Annotated[User, Depends(current_user)]
_DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate, user: _CurrentUser, db: _DB
) -> Conversation:
    """Create a new conversation linked to a knowledge base.

    Parameters
    ----------
    body : ConversationCreate
        Target knowledge base UUID and optional title.
    user : User
        Authenticated user; must own the knowledge base.
    db : AsyncSession
        Database session.

    Returns
    -------
    Conversation
        Newly created conversation row.

    Raises
    ------
    HTTPException
        404 when the knowledge base does not exist or is not owned by the user.
    """
    await _assert_kb_owned(body.kb_id, user, db)
    conv = Conversation(user_id=user.id, kb_id=body.kb_id, title=body.title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("", response_model=list[ConversationRead])
async def list_conversations(user: _CurrentUser, db: _DB) -> list[Conversation]:
    """List all conversations for the authenticated user.

    Parameters
    ----------
    user : User
        Authenticated user.
    db : AsyncSession
        Database session.

    Returns
    -------
    list[Conversation]
        Conversations ordered by most-recently-updated first.
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{conv_id}", response_model=ConversationDetail)
async def get_conversation(
    conv_id: uuid.UUID, user: _CurrentUser, db: _DB
) -> Conversation:
    """Fetch a conversation with its full message history.

    Parameters
    ----------
    conv_id : uuid.UUID
        Conversation identifier.
    user : User
        Authenticated user; must own the conversation.
    db : AsyncSession
        Database session.

    Returns
    -------
    Conversation
        Conversation row with eagerly loaded messages.

    Raises
    ------
    HTTPException
        404 when the conversation does not exist or is not owned by the user.
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conv_id, Conversation.user_id == user.id)
        .options(selectinload(Conversation.messages))
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conv_id: uuid.UUID, user: _CurrentUser, db: _DB
) -> None:
    """Delete a conversation and all its messages.

    Parameters
    ----------
    conv_id : uuid.UUID
        Conversation identifier.
    user : User
        Authenticated user; must own the conversation.
    db : AsyncSession
        Database session.

    Raises
    ------
    HTTPException
        404 when the conversation does not exist or is not owned by the user.
    """
    conv = await _get_owned(conv_id, user, db)
    await db.delete(conv)
    await db.commit()


@router.post("/{conv_id}/chat", response_model=ChatResponse)
async def chat(
    conv_id: uuid.UUID,
    body: ChatRequest,
    user: _CurrentUser,
    db: _DB,
    request: Request,
) -> ChatResponse:
    """Run the CRAG agent and persist the exchange as user + assistant messages.

    Parameters
    ----------
    conv_id : uuid.UUID
        Conversation to append to.
    body : ChatRequest
        User message content.
    user : User
        Authenticated user; must own the conversation.
    db : AsyncSession
        Database session.
    request : Request
        FastAPI request object; used to access ``app.state.agent_graph``.

    Returns
    -------
    ChatResponse
        Agent answer, citations, and conversation ID.

    Raises
    ------
    HTTPException
        404 when the conversation does not exist or is not owned by the user.
    """
    conv = await _get_owned(conv_id, user, db)

    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
        .limit(20)
    )
    history = [
        {"role": m.role.value, "content": m.content}
        for m in history_result.scalars().all()
    ]

    turn_index = len(history) // 2

    if conv.mlflow_run_id is None:
        run_id = open_conversation_run(
            conversation_id=str(conv.id),
            kb_id=str(conv.kb_id) if conv.kb_id else None,
            title=conv.title,
        )
        if run_id:
            conv.mlflow_run_id = run_id
            await db.commit()
            await db.refresh(conv)

    user_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.user,
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    graph = request.app.state.agent_graph
    initial_state: AgentState = {
        "query": body.message,
        "kb_id": str(conv.kb_id) if conv.kb_id else "",
        "history": history,
        "documents": [],
        "answer": "",
        "citations": [],
        "needs_web_search": False,
        "generation_count": 0,
        "hallucination_detected": False,
        "retrieved_count": 0,
    }

    t0 = time.monotonic()
    async with agent_run_context(conv.mlflow_run_id, str(conv.id), turn_index):
        final_state: AgentState = await graph.ainvoke(initial_state)
    latency_ms = int((time.monotonic() - t0) * 1000)

    log_turn_metrics(
        conv.mlflow_run_id,
        turn_index=turn_index,
        retrieved_docs=final_state.get("retrieved_count", 0),
        relevant_docs=len(final_state.get("documents", [])),
        needs_web_search=bool(final_state.get("needs_web_search")),
        generation_count=final_state.get("generation_count", 1),
        hallucination_detected=bool(final_state.get("hallucination_detected")),
        latency_ms=latency_ms,
    )

    asst_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.assistant,
        content=final_state["answer"],
    )
    db.add(asst_msg)
    await db.flush()

    citation_reads: list[CitationRead] = []
    for cit in final_state.get("citations", []):
        raw_id = cit.get("chunk_id")
        chunk_uuid: uuid.UUID | None = None
        if raw_id:
            try:
                chunk_uuid = uuid.UUID(str(raw_id))
                db.add(
                    MessageCitation(
                        message_id=asst_msg.id,
                        chunk_id=chunk_uuid,
                        score=float(cit["score"]),
                    )
                )
            except (ValueError, TypeError):
                pass
        citation_reads.append(CitationRead(chunk_id=chunk_uuid, score=float(cit.get("score", 0.0))))

    await db.commit()

    return ChatResponse(
        answer=final_state["answer"],
        citations=citation_reads,
        conversation_id=conv.id,
    )


async def _get_owned(conv_id: uuid.UUID, user: User, db: AsyncSession) -> Conversation:
    """Fetch a conversation that must be owned by *user*.

    Parameters
    ----------
    conv_id : uuid.UUID
        Conversation identifier.
    user : User
        Authenticated user.
    db : AsyncSession
        Database session.

    Returns
    -------
    Conversation
        Matching row.

    Raises
    ------
    HTTPException
        404 when no matching owned conversation is found.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == user.id
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


async def _assert_kb_owned(kb_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    """Raise 404 when the knowledge base does not exist or is not owned by *user*.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    user : User
        Authenticated user.
    db : AsyncSession
        Database session.

    Raises
    ------
    HTTPException
        404 when ownership check fails.
    """
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
