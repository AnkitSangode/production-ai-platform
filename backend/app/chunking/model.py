
from dataclasses import dataclass
from uuid import UUID

@dataclass(slots=True, frozen=True)
class Chunk:
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    page_number: int
    text: str