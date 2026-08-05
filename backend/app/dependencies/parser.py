from functools import lru_cache

from app.parser.base import ParserService

from app.parser.pdf import PdfParserService


@lru_cache
def get_parser_service() -> ParserService:
    return PdfParserService()