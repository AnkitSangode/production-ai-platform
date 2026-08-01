from sqlalchemy.orm import Session

from app.storage.local import StorageService

from app.db.models.user import User

from app.db.models.document import Document

from app.db.models.outbox_event import OutboxEvent

from fastapi import UploadFile

from app.repositories.document_repository import DocumentRepository

from app.repositories.outbox_repository import OutboxRepository

from app.enums.outbox import EventType


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        outbox_repository: OutboxRepository,
        storage: StorageService,
        db: Session,
    ):
        self.repository = repository
        self.storage = storage
        self.db = db
        self.outbox_repository = outbox_repository

    def upload_document(self, file: UploadFile, current_user: User) -> Document:

        storage_key = self.storage.generate_storage_key(file.filename)
        file_size = self.storage.store(file, storage_key)

        document = Document(
            user_id=current_user.id,
            original_filename=file.filename,
            storage_key=storage_key,
            content_type=file.content_type,
            file_size=file_size,
        )

        event = OutboxEvent(
            document_id=document.id,
            event_type=EventType.DOCUMENT_UPLOADED,
            payload={
                "document_id": str(document.id),
            },
        )

        try:
            self.repository.create(document)
            self.outbox_repository.create(event)
            self.db.commit()

            return document

        except Exception:
            self.db.rollback()

            try:
                self.storage.delete(storage_key)
            except Exception:
                pass

            raise
