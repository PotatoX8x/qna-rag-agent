from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.orm.base import Base, TimestampMixin, UUIDMixin


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    kb_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.pending, nullable=False
    )
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    knowledge_base: Mapped[KnowledgeBase] = relationship(  # type: ignore[name-defined]
        "KnowledgeBase", back_populates="documents"
    )
    chunks: Mapped[list[Chunk]] = relationship(  # type: ignore[name-defined]
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )
