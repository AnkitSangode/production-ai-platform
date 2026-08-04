from abc import ABC, abstractmethod

from fastapi import UploadFile

from collections.abc import Generator

from typing import BinaryIO


class StorageService(ABC):
    @abstractmethod
    def generate_storage_key(self, filename: str) -> str:
        """Generate a unique storage key for the uploaded file."""
        ...

    @abstractmethod
    def store(self, file: UploadFile, storage_key: str) -> int:
        """Store the uploaded file."""
        ...

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Delete a stored file."""
        ...

    @abstractmethod
    def retrieve_stream(self, storage_key: str) -> Generator[bytes, None, None]:
        """Retrieve a stored file while downloading the file"""
        ...

    @abstractmethod
    def retrieve(self,storage_key:str) -> BinaryIO:
        """Retrieve a stored file"""