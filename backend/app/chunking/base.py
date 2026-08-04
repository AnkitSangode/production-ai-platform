from abc import ABC, abstractmethod
from uuid import UUID

from .model import Chunk


class ChunkingService(ABC):
    """Converts parsed pages into Chunk objects."""

    @abstractmethod
    def chunk(
        self,
        document_id: UUID,
        pages: list[str],
    ) -> list[Chunk]: ...
