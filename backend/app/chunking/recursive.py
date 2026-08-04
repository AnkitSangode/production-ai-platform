from uuid import UUID, uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import ChunkingService
from .model import Chunk

class LangChainChunkingService(ChunkingService):

    def __init__(self,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str] | None = None):

    def chunk(
        self,
        document_id: UUID,
        pages: list[str],
    ) -> list[Chunk]:
        ...