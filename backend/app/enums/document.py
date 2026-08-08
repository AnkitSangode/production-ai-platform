from enum import StrEnum, Enum


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class DocumentContentType(str, Enum):
    PDF = "application/pdf"

    @classmethod
    def values(cls) -> set[str]:
        return {content_type.value for content_type in cls}