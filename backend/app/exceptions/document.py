from app.exceptions.base import DomainError


class DocumentError(DomainError):
    """Base class for document-related errors."""
    pass


class UnsupportedFileTypeError(DocumentError):
    def __init__(self):
        super().__init__("The uploaded file type is not supported.")


class DocumentTooLargeError(DocumentError):
    def __init__(self, actual_size: int, max_size: int):
        self.actual_size = actual_size
        self.max_size = max_size

        super().__init__(
            f"Document size {actual_size} exceeds maximum allowed size {max_size}."
        )


class DocumentNotFoundError(DocumentError):
    def __init__(self):
        super().__init__("The requested document was not found.")


class EmptyFileError(DocumentError):
    def __init__(self):
        super().__init__("The uploaded file is empty.")


class DocumentAccessDeniedError(DocumentError):
    def __init__(self):
        super().__init__("Access to this document is denied.")