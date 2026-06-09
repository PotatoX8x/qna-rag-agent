from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.ingest_document", bind=True, max_retries=3)
def ingest_document(self, document_id: str, kb_id: str) -> dict:
    """Load, chunk, embed and store a document. Implemented in Phase 4."""
    raise NotImplementedError("Ingestion pipeline arrives in Phase 4")
