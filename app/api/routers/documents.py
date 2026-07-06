import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import current_user
from app.api.dependencies.db import get_db
from app.api.schemas.document import DocumentRead
from app.container import ServiceContainer
from app.db.orm.document import Document
from app.db.orm.knowledge_base import KnowledgeBase
from app.db.orm.user import User
from app.ingestion.loaders import allowed_suffix, sniff_content_type

router = APIRouter(prefix="/knowledge-bases/{kb_id}/documents", tags=["documents"])

_CurrentUser = Annotated[User, Depends(current_user)]
_DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[DocumentRead])
async def list_documents(kb_id: uuid.UUID, user: _CurrentUser, db: _DB) -> list[Document]:
    """List all documents in a knowledge base.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    user : User
        Authenticated user; must own the knowledge base.
    db : AsyncSession
        Database session.

    Returns
    -------
    list[Document]
        Documents ordered by creation date descending.

    Raises
    ------
    HTTPException
        404 when the knowledge base is not found or not owned by the user.
    """
    await _assert_kb_owned(kb_id, user, db)
    result = await db.execute(
        select(Document).where(Document.kb_id == kb_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    kb_id: uuid.UUID,
    file: UploadFile,
    user: _CurrentUser,
    db: _DB,
) -> Document:
    """Upload a document and enqueue it for background ingestion.

    The document row is created immediately with ``status=pending``; the Celery
    worker updates it to ``processing`` → ``ready`` (or ``failed``) asynchronously.

    Parameters
    ----------
    kb_id : uuid.UUID
        Target knowledge base.
    file : UploadFile
        Multipart file upload. Accepted extensions: pdf, docx, pptx, xlsx, txt, md, html, csv.
    user : User
        Authenticated user; must own the knowledge base.
    db : AsyncSession
        Database session.

    Returns
    -------
    Document
        Newly created document row with ``status=pending``.

    Raises
    ------
    HTTPException
        404 when the knowledge base is not found, 415 for unsupported file types.
    """
    await _assert_kb_owned(kb_id, user, db)

    filename = file.filename or "upload"
    if not allowed_suffix(filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Allowed: pdf, docx, pptx, xlsx, txt, md, html, csv",
        )
    content_type = file.content_type or sniff_content_type(filename)

    doc = Document(kb_id=kb_id, filename=filename, content_type=content_type)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    services = ServiceContainer.get_instance()
    upload_dir = Path(services.config["database"]["data_dir"]) / "uploads" / str(doc.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    (upload_dir / doc.filename).write_bytes(content)

    from app.worker.tasks import ingest_document
    ingest_document.delay(str(doc.id), str(kb_id))

    return doc


@router.get("/{doc_id}", response_model=DocumentRead)
async def get_document(kb_id: uuid.UUID, doc_id: uuid.UUID, user: _CurrentUser, db: _DB) -> Document:
    """Fetch a single document, typically to poll its ingestion status.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    doc_id : uuid.UUID
        Document identifier.
    user : User
        Authenticated user; must own the knowledge base.
    db : AsyncSession
        Database session.

    Returns
    -------
    Document
        Matching document row.

    Raises
    ------
    HTTPException
        404 when the knowledge base or document is not found.
    """
    await _assert_kb_owned(kb_id, user, db)
    return await _get_doc(doc_id, kb_id, db)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(kb_id: uuid.UUID, doc_id: uuid.UUID, user: _CurrentUser, db: _DB) -> None:
    """Delete a document and its chunks.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    doc_id : uuid.UUID
        Document identifier.
    user : User
        Authenticated user; must own the knowledge base.
    db : AsyncSession
        Database session.

    Raises
    ------
    HTTPException
        404 when the knowledge base or document is not found.
    """
    await _assert_kb_owned(kb_id, user, db)
    doc = await _get_doc(doc_id, kb_id, db)
    await db.delete(doc)
    await db.commit()

    # Clear the documents even when they are deleted while still pending/processing.
    services = ServiceContainer.get_instance()
    upload_dir = Path(services.config["database"]["data_dir"]) / "uploads" / str(doc_id)
    shutil.rmtree(upload_dir, ignore_errors=True)


async def _assert_kb_owned(kb_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    """Raise 404 when the knowledge base does not exist or is not owned by ``user``.

    Parameters
    ----------
    kb_id : uuid.UUID
        Knowledge base identifier.
    user : User
        Authenticated user.
    db : AsyncSession
        Database session.

    Raises
    ------
    HTTPException
        404 when ownership check fails.
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")


async def _get_doc(doc_id: uuid.UUID, kb_id: uuid.UUID, db: AsyncSession) -> Document:
    """Fetch a document that must belong to the given knowledge base.

    Parameters
    ----------
    doc_id : uuid.UUID
        Document identifier.
    kb_id : uuid.UUID
        Knowledge base the document must belong to.
    db : AsyncSession
        Database session.

    Returns
    -------
    Document
        Matching document row.

    Raises
    ------
    HTTPException
        404 when no matching document is found.
    """
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.kb_id == kb_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc
