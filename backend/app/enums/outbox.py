from enum import StrEnum


class EventType(StrEnum):
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSING_STARTED = "document.processing.started"
    DOCUMENT_READY = "document.ready"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_FAILED = "document.failed"