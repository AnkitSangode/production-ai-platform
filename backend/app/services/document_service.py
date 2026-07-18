from sqlalchemy.orm import Session

from app.storage.local import StorageService

from app.db.models.user import User

from app.db.models.document import Document

from fastapi import UploadFile

from app.repositories.document_repository import DocumentRepository


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: StorageService,
        db: Session,
    ):
        self.repository = repository
        self.storage = storage
        self.db = db

    def upload_document(self,file: UploadFile,current_user: User) -> Document:

        storage_key = self.storage.generate_storage_key(file.filename)
        file_size = self.storage.store(file, storage_key)

        document =  Document(
            user_id = current_user.id,
            original_filename = file.filename,
            storage_key = storage_key,
            content_type = file.content_type,
            file_size = file_size
        )

        try:
            self.repository.create(document)
            self.db.commit()

            return document

        except Exception:
            self.db.rollback()


            try:
                self.storage.delete(storage_key)

            except Exception:
                pass