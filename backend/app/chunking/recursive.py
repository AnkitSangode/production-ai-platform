from uuid import UUID, uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import ChunkingService
from .model import Chunk


class LangChainChunkingService(ChunkingService):

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str] | None = None,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators
            or [
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )

    def chunk(
        self,
        document_id: UUID,
        pages: list[str],
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 0

        for page_number, page in enumerate(
            pages,
            start=1,
        ):
            pieces = self._splitter.split_text(page)

            for piece in pieces:
                chunks.append(
                    Chunk(
                        chunk_id=uuid4(),
                        document_id=document_id,
                        chunk_index=chunk_index,
                        page_number=page_number,
                        text=piece,
                    )
                )
                chunk_index += 1
        return chunks
