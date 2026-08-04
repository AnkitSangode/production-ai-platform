from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .base import ParserService
from .exceptions import DocumentParsingError


class PdfParserService(ParserService):

    def parse(self, file: BinaryIO) -> list[str]:
        try:
            reader = PdfReader(file)

            pages: list[str] = []

            for page in reader.pages:
                text = page.extract_text()
                pages.append(text or "")

            return pages

        except PdfReadError as e:
            raise DocumentParsingError(
                "Failed to parse PDF document."
            ) from e