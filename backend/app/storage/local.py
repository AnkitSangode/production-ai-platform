from pathlib import Path

from app.core.config import Settings

from app.storage.base import StorageService

from uuid import uuid4

from fastapi import UploadFile


class LocalStorageService(StorageService):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.upload_dir = Path(settings.UPLOAD_DIR)

        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def generate_storage_key(self,filename: str,) -> str:
        extension = Path(filename).suffix

        return f"{uuid4()}{extension}"
        
    def store(
    self,
    file: UploadFile,
    storage_key: str,
    ) -> None:
        file_path = self.upload_dir / storage_key
        with open(file_path, "wb") as destination:
            try:
                while True:
                    chunk = file.file.read(1024*1024)

                    if not chunk:
                        break
                    destination.write(chunk)
            except Exception:
                if file_path.exists():
                    file_path.unlink()
                raise 