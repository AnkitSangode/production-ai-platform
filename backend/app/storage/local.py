from collections.abc import Generator
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings
from app.storage.base import StorageService, StorageResult
from app.exceptions.storage import StorageLimitExceededError


class LocalStorageService(StorageService):
    CHUNK_SIZE = 1024 * 1024  # 1 MB

    def __init__(self, settings: Settings):
        self.settings = settings
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _generate_storage_key(self, filename: str) -> str:
        extension = Path(filename).suffix
        return f"{uuid4()}{extension}"

    def store(
        self,
        file: UploadFile,
    ) -> StorageResult:
        storage_key = self._generate_storage_key(file.filename)

        file_path = self.upload_dir / storage_key
        file_size = 0
        max_size = self.settings.MAX_DOCUMENT_SIZE

        try:
            with open(file_path, "wb") as destination:
                while True:
                    chunk = file.file.read(self.CHUNK_SIZE)

                    if not chunk:
                        break

                    chunk_size = len(chunk)

                    if file_size + chunk_size > max_size:
                        raise StorageLimitExceededError(
                            actual_size=file_size + chunk_size,
                            max_size=max_size,
                        )

                    destination.write(chunk)
                    file_size += len(chunk)

            return StorageResult(
                storage_key=storage_key,
                file_size=file_size,
            )

        except Exception:
            if file_path.exists():
                file_path.unlink()

            raise

    def retrieve(
        self,
        storage_key: str,
    ) -> BinaryIO:
        file_path = self.upload_dir / storage_key

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")

        return open(file_path, "rb")

    def retrieve_stream(
        self,
        storage_key: str,
    ) -> Generator[bytes, None, None]:
        file_path = self.upload_dir / storage_key

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")

        with open(file_path, "rb") as source:
            while True:
                chunk = source.read(self.CHUNK_SIZE)

                if not chunk:
                    break

                yield chunk

    def delete(
        self,
        storage_key: str,
    ) -> None:
        file_path = self.upload_dir / storage_key

        if file_path.exists():
            file_path.unlink()