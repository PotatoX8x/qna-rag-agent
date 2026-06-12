import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import current_user
from app.api.dependencies.db import get_db
from app.api.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseRead
from app.db.orm.knowledge_base import KnowledgeBase
from app.db.orm.user import User

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])

_CurrentUser = Annotated[User, Depends(current_user)]
_DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[KnowledgeBaseRead])
async def list_knowledge_bases(user: _CurrentUser, db: _DB) -> list[KnowledgeBase]:
    """List all knowledge bases owned by the authenticated user.

    Parameters
    ----------
    user : User
        Authenticated user from JWT.
    db : AsyncSession
        Database session.

    Returns
    -------
    list[KnowledgeBase]
        Knowledge bases ordered by creation date descending.
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == user.id).order_by(KnowledgeBase.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(body: KnowledgeBaseCreate, user: _CurrentUser, db: _DB) -> KnowledgeBase:
    """Create a new knowledge base for the authenticated user.

    Parameters
    ----------
    body : KnowledgeBaseCreate
        Name and optional description.
    user : User
        Authenticated user from JWT.
    db : AsyncSession
        Database session.

    Returns
    -------
    KnowledgeBase
        Newly created knowledge base row.
    """
    kb = KnowledgeBase(user_id=user.id, name=body.name, description=body.description)
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_knowledge_base(kb_id: uuid.UUID, user: _CurrentUser, db: _DB) -> KnowledgeBase:
    """Fetch a single knowledge base by ID.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    user : User
        Authenticated user; must own the knowledge base.
    db : AsyncSession
        Database session.

    Returns
    -------
    KnowledgeBase
        Matching knowledge base row.

    Raises
    ------
    HTTPException
        404 when the knowledge base does not exist or is not owned by the user.
    """
    return await _get_owned(kb_id, user, db)


@router.patch("/{kb_id}", response_model=KnowledgeBaseRead)
async def update_knowledge_base(
    kb_id: uuid.UUID, body: KnowledgeBaseCreate, user: _CurrentUser, db: _DB
) -> KnowledgeBase:
    """Update the name and/or description of a knowledge base.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    body : KnowledgeBaseCreate
        Fields to update.
    user : User
        Authenticated user; must own the knowledge base.
    db : AsyncSession
        Database session.

    Returns
    -------
    KnowledgeBase
        Updated knowledge base row.

    Raises
    ------
    HTTPException
        404 when the knowledge base does not exist or is not owned by the user.
    """
    kb = await _get_owned(kb_id, user, db)
    kb.name = body.name
    if body.description is not None:
        kb.description = body.description
    await db.commit()
    await db.refresh(kb)
    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(kb_id: uuid.UUID, user: _CurrentUser, db: _DB) -> None:
    """Delete a knowledge base and all its documents and chunks.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    user : User
        Authenticated user; must own the knowledge base.
    db : AsyncSession
        Database session.

    Raises
    ------
    HTTPException
        404 when the knowledge base does not exist or is not owned by the user.
    """
    kb = await _get_owned(kb_id, user, db)
    await db.delete(kb)
    await db.commit()


async def _get_owned(kb_id: uuid.UUID, user: User, db: AsyncSession) -> KnowledgeBase:
    """Fetch a knowledge base that must be owned by ``user``.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    user : User
        Authenticated user.
    db : AsyncSession
        Database session.

    Returns
    -------
    KnowledgeBase
        Matching row.

    Raises
    ------
    HTTPException
        404 when no matching owned knowledge base is found.
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id)
    )
    kb = result.scalar_one_or_none()
    if kb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return kb
