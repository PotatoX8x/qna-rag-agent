from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.orm.base import Base, TimestampMixin, UUIDMixin


class KnowledgeBase(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_bases"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="knowledge_bases")  # type: ignore[name-defined]
    documents: Mapped[list[Document]] = relationship(  # type: ignore[name-defined]
        "Document", back_populates="knowledge_base", cascade="all, delete-orphan"
    )
    chunks: Mapped[list[Chunk]] = relationship(  # type: ignore[name-defined]
        "Chunk", back_populates="knowledge_base", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[Conversation]] = relationship(  # type: ignore[name-defined]
        "Conversation", back_populates="knowledge_base"
    )
