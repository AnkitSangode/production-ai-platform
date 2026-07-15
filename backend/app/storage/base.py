from abc import ABC, abstractmethod

from fastapi import UploadFile


class StorageService(ABC):
    @abstractmethod
    def generate_storage_key(self, filename: str) -> str:
        """Generate a unique storage key for the uploaded file."""
        ...

    @abstractmethod
    def store(self, file: UploadFile, storage_key: str) -> None:
        """Store the uploaded file."""
        ...

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Delete a stored file."""
        ...

    @abstractmethod
    def retrieve(self, storage_key: str):
        """Retrieve a stored file."""
        ...