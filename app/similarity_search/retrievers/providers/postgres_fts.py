from __future__ import annotations

import re
from typing import Any, Optional

from langchain_core.documents import Document

from app.similarity_search.retrievers.base import BaseRetriever, ScoredDocs
from app.similarity_search.vectorstore.base import BaseVectorStore


def _to_sync_url(url: str) -> str:
    """Strip the async driver prefix from a SQLAlchemy database URL.

    Parameters
    ----------
    url : str
        URL that may contain a ``+asyncpg`` or ``+psycopg`` driver suffix.

    Returns
    -------
    str
        Plain ``postgresql://`` URL suitable for psycopg sync connections.
    """
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


class PostgresFTSRetriever(BaseRetriever):
    """Lexical retrieval using Postgres full-text search (``tsvector`` + ``ts_rank``)."""

    def __init__(self, vectorstore_client: BaseVectorStore, url: str = None, **kwargs) -> None:
        """
        Parameters
        ----------
        vectorstore_client : BaseVectorStore
            Used as a fallback source for the connection URL when the store
            is a ``PgVectorStore`` (exposes ``.conninfo``).
        url : str or None, optional
            Explicit database URL. Takes priority over the store's ``conninfo``.

        Raises
        ------
        ValueError
            When neither ``url`` nor a ``PgVectorStore`` with ``.conninfo`` is provided.
        """
        self.vectorstore_client = vectorstore_client
        raw_url = url or getattr(vectorstore_client, "conninfo", None)
        if not raw_url:
            raise ValueError(
                "PostgresFTSRetriever requires a 'url' kwarg or a PgVectorStore client with .conninfo"
            )
        self._conninfo = _to_sync_url(raw_url)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_normalization: Optional[str] = None,
        metadata_filter: Optional[dict[str, Any]] = None,
    ) -> ScoredDocs:
        """Run a full-text search using ``websearch_to_tsquery`` and rank with ``ts_rank``.

        Parameters
        ----------
        query : str
            User query string parsed via ``websearch_to_tsquery``.
        top_k : int, optional
            Maximum results to return. Default is 5.
        score_normalization : str or None, optional
            Normalisation method to apply after ranking.
        metadata_filter : dict or None, optional
            Column equality conditions applied as additional ``WHERE`` clauses.

        Returns
        -------
        ScoredDocs
            List of ``(Document, ts_rank_score)`` pairs, highest score first.
        """
        import psycopg

        where_parts = ["c.tsv @@ q.tsq"]
        filter_params: list = [query]

        for key, value in (metadata_filter or {}).items():
            if isinstance(value, list):
                where_parts.append(f"c.{key} = ANY(%s::uuid[])")
                filter_params.append([str(v) for v in value])
            else:
                where_parts.append(f"c.{key} = %s::uuid")
                filter_params.append(str(value))

        filter_params.append(top_k)

        sql = f"""
            WITH q AS (SELECT websearch_to_tsquery('english', %s) AS tsq)
            SELECT c.content, c.chunk_metadata, c.id::text, c.kb_id::text, c.doc_id::text,
                   ts_rank(c.tsv, q.tsq) AS score
            FROM chunks c, q
            WHERE {' AND '.join(where_parts)}
            ORDER BY score DESC
            LIMIT %s
        """

        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, filter_params)
                rows = cur.fetchall()

        scored: ScoredDocs = [
            (
                Document(
                    page_content=content,
                    metadata={**(meta or {}), "id": cid, "kb_id": kid, "doc_id": did},
                ),
                float(score),
            )
            for content, meta, cid, kid, did, score in rows
        ]
        return self._apply_normalization(scored, score_normalization)
