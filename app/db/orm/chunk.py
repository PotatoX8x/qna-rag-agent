from __future__ import annotations

import uuid
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.orm.base import Base, TimestampMixin, UUIDMixin

EMBEDDING_DIM = 384


class Chunk(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chunks"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    kb_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    tsv: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")  # type: ignore[name-defined]
    knowledge_base: Mapped[KnowledgeBase] = relationship("KnowledgeBase", back_populates="chunks")  # type: ignore[name-defined]
    citations: Mapped[list[MessageCitation]] = relationship(  # type: ignore[name-defined]
        "MessageCitation", back_populates="chunk", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
    )
