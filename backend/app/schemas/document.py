from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.enums.document import DocumentStatus


class DocumentResponse(BaseModel):
    

    id: UUID
    filename: str
    file_size: int
    status: DocumentStatus
    created_at: datetime


class UploadDocumentRequest(BaseModel):
    title: str | None
    workspace_id: UUID
    visibility: Visibility
    tags: list[str]