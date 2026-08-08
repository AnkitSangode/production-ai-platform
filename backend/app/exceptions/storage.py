from app.exceptions.base import DomainError


class StorageError(DomainError):
    """Base exception for storage-related errors."""

    pass


class StorageLimitExceededError(StorageError):
    def __init__(self, actual_size: int, max_size: int):
        self.actual_size = actual_size
        self.max_size = max_size

        super().__init__(
            f"Stored file size {actual_size} exceeds "
            f"maximum allowed size {max_size}."
        )