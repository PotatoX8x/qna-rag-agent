from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.embedding_client.base import BaseEmbeddingClient


def chunk_text(text: str, embedding_client: BaseEmbeddingClient) -> list[str]:
    """Split text at semantic boundaries detected by the app's own embedding model.

    Parameters
    ----------
    text : str
        Full document text to split.
    embedding_client : BaseEmbeddingClient
        Embedding client used by ``SemanticChunker`` to locate topic boundaries.

    Returns
    -------
    list[str]
        Non-empty chunks aligned with semantic topic shifts.
    """
    from langchain_experimental.text_splitter import SemanticChunker

    chunker = SemanticChunker(
        embeddings=embedding_client,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=95,
    )
    return [c for c in chunker.split_text(text) if c.strip()]
