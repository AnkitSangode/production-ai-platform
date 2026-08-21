from enum import StrEnum, Enum


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class DocumentClaimResult(StrEnum):
    CLAIMED = "CLAIMED"
    ALREADY_OWNED = "ALREADY_OWNED"
    OWNED_BY_OTHER = "OWNED_BY_OTHER"


class DocumentProcessingStage(StrEnum):
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"


class DocumentContentType(str, Enum):
    PDF = "application/pdf"

    @classmethod
    def values(cls) -> set[str]:
        return {content_type.value for content_type in cls}
