import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.db.orm.document import DocumentStatus


class DocumentRead(BaseModel):
    id: uuid.UUID
    kb_id: uuid.UUID
    filename: str
    content_type: str
    status: DocumentStatus
    error_msg: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
