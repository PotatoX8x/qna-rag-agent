from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    """Request body for creating a new conversation."""

    kb_id: Optional[uuid.UUID] = None
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    """Request body for updating a conversation's knowledge base or title."""

    kb_id: Optional[uuid.UUID] = None
    title: Optional[str] = None


class ConversationRead(BaseModel):
    """Serialised view of a ``Conversation`` ORM row."""

    id: uuid.UUID
    kb_id: Optional[uuid.UUID]
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CitationRead(BaseModel):
    """A single grounded citation returned alongside an answer."""

    index: Optional[int] = None
    chunk_id: Optional[uuid.UUID] = None
    score: float
    snippet: Optional[str] = None

    model_config = {"from_attributes": True}


class MessageRead(BaseModel):
    """Serialised view of a ``Message`` ORM row."""

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    citations: list[CitationRead] = []

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationRead):
    """``ConversationRead`` enriched with its ordered message history."""

    messages: list[MessageRead]


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Response body for the chat endpoint."""

    answer: str
    citations: list[CitationRead]
    conversation_id: uuid.UUID
