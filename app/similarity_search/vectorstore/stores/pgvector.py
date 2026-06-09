from __future__ import annotations

import json
import re
import uuid
from typing import Optional

from langchain_core.documents import Document

from app.models.embedding_client.base import BaseEmbeddingClient
from app.similarity_search.vectorstore.base import BaseVectorStore


def _to_sync_url(url: str) -> str:
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


def _build_where(metadata_filter: Optional[dict]) -> tuple[str, list]:
    if not metadata_filter:
        return "", []
    parts = []
    params: list = []
    for key, value in metadata_filter.items():
        col = key
        if isinstance(value, list):
            parts.append(f"{col} = ANY(%s::uuid[])")
            params.append([str(v) for v in value])
        else:
            parts.append(f"{col} = %s::uuid")
            params.append(str(value))
    return " AND ".join(parts), params


class PgVectorStore(BaseVectorStore):
    """pgvector-backed store. Reads/writes the ``chunks`` table using a sync psycopg connection."""

    def __init__(self, embedding_client: BaseEmbeddingClient, collection_name: str, url: str, **kwargs) -> None:
        self.embedding_client = embedding_client
        self.collection_name = collection_name
        self.conninfo = _to_sync_url(url)

    def _connect(self):
        import psycopg
        from pgvector.psycopg import register_vector

        conn = psycopg.connect(self.conninfo)
        register_vector(conn)
        return conn

    def add_documents(self, documents: list[Document]) -> None:
        if not documents:
            return
        texts = [doc.page_content for doc in documents]
        embeddings = self.embedding_client.embed_documents(texts)

        with self._connect() as conn:
            with conn.cursor() as cur:
                for doc, embedding in zip(documents, embeddings):
                    meta = dict(doc.metadata or {})
                    chunk_id = meta.get("id") or str(uuid.uuid4())
                    doc_id = meta.get("doc_id")
                    kb_id = meta.get("kb_id")
                    chunk_index = meta.get("chunk_index", 0)
                    cur.execute(
                        """
                        INSERT INTO chunks (id, doc_id, kb_id, content, chunk_index, chunk_metadata, embedding)
                        VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, %s::jsonb, %s)
                        ON CONFLICT (id) DO UPDATE
                            SET content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding,
                                chunk_metadata = EXCLUDED.chunk_metadata
                        """,
                        (chunk_id, doc_id, kb_id, doc.page_content, chunk_index, json.dumps(meta), embedding),
                    )
            conn.commit()

    def query(self, query: str, top_k: int = 5, metadata_filter: Optional[dict] = None) -> list[tuple[Document, float]]:
        q_emb = self.embedding_client.embed_query(query)
        where_cond, params = _build_where(metadata_filter)
        where_clause = f"AND {where_cond}" if where_cond else ""

        sql = f"""
            WITH q AS (SELECT %s::vector AS emb)
            SELECT c.content, c.chunk_metadata, c.id::text, c.kb_id::text, c.doc_id::text,
                   1 - (c.embedding <=> q.emb) AS score
            FROM chunks c, q
            WHERE c.embedding IS NOT NULL {where_clause}
            ORDER BY c.embedding <=> q.emb
            LIMIT %s
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, [q_emb, *params, top_k])
                rows = cur.fetchall()

        return [
            (
                Document(
                    page_content=content,
                    metadata={**(meta or {}), "id": cid, "kb_id": kid, "doc_id": did},
                ),
                float(score),
            )
            for content, meta, cid, kid, did, score in rows
        ]

    def get_collection(self, metadata_filter: Optional[dict] = None) -> list[Document]:
        where_cond, params = _build_where(metadata_filter)
        where_clause = f"WHERE {where_cond}" if where_cond else ""
        sql = f"""
            SELECT content, chunk_metadata, id::text, kb_id::text, doc_id::text
            FROM chunks {where_clause}
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        return [
            Document(
                page_content=content,
                metadata={**(meta or {}), "id": cid, "kb_id": kid, "doc_id": did},
            )
            for content, meta, cid, kid, did in rows
        ]

    def clear(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks")
            conn.commit()

    def reset_collection(self) -> None:
        self.clear()
