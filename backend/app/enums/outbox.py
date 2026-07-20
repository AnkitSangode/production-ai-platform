from enum import StrEnum, auto


class EventType(StrEnum):
    DOCUMENT_UPLOADED = auto()
    DOCUMENT_PROCESSING_STARTED = auto()
    DOCUMENT_READY = auto()
    DOCUMENT_DELETED = auto()
    DOCUMENT_FAILED = auto()