from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.orm.base import Base, TimestampMixin, UUIDMixin


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped[Conversation] = relationship(  # type: ignore[name-defined]
        "Conversation", back_populates="messages"
    )
    citations: Mapped[list[MessageCitation]] = relationship(  # type: ignore[name-defined]
        "MessageCitation", back_populates="message", cascade="all, delete-orphan"
    )


class MessageCitation(UUIDMixin, Base):
    __tablename__ = "message_citations"

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)

    message: Mapped[Message] = relationship("Message", back_populates="citations")
    chunk: Mapped[Chunk] = relationship("Chunk", back_populates="citations")  # type: ignore[name-defined]
