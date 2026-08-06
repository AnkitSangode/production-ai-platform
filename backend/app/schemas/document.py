from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.document import 


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    file_size: int
    status: DocumentStatus
    created_at: datetime