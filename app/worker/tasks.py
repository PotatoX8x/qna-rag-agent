import re
import uuid
from pathlib import Path

import psycopg
from langchain_core.documents import Document

from app.worker.celery_app import celery_app


def _sync_url(url: str) -> str:
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


@celery_app.task(name="app.worker.tasks.ingest_document", bind=True, max_retries=3)
def ingest_document(self, document_id: str, kb_id: str) -> dict:
    from app.container import ServiceContainer
    from app.ingestion.chunker import chunk_text
    from app.ingestion.loaders import load_file
    from app.similarity_search.vectorstore.stores.pgvector import PgVectorStore

    services = ServiceContainer.get_instance()
    db_url = services.config["database"]["url"]
    conninfo = _sync_url(db_url)
    upload_dir = Path(services.config["database"]["data_dir"]) / "uploads" / document_id

    try:
        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET status = 'processing', updated_at = now() WHERE id = %s::uuid",
                    (document_id,),
                )
                cur.execute(
                    "SELECT filename FROM documents WHERE id = %s::uuid",
                    (document_id,),
                )
                row = cur.fetchone()
            conn.commit()

        if row is None:
            raise ValueError(f"Document {document_id} not found")

        (filename,) = row
        text = load_file(upload_dir / filename)
        raw_chunks = chunk_text(text, services.embeddings)

        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "id": str(uuid.uuid4()),
                    "doc_id": document_id,
                    "kb_id": kb_id,
                    "chunk_index": i,
                },
            )
            for i, chunk in enumerate(raw_chunks)
        ]

        store = PgVectorStore(
            embedding_client=services.embeddings,
            collection_name=kb_id,
            url=db_url,
        )
        store.add_documents(docs)

        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET status = 'ready', updated_at = now() WHERE id = %s::uuid",
                    (document_id,),
                )
            conn.commit()

        return {"document_id": document_id, "chunks": len(docs)}

    except Exception as exc:
        try:
            with psycopg.connect(conninfo) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE documents SET status = 'failed', error_msg = %s, updated_at = now() "
                        "WHERE id = %s::uuid",
                        (str(exc)[:2000], document_id),
                    )
                conn.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=30)
