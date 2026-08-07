from sqlalchemy.orm import Session

from app.storage.local import StorageService

from app.core.logging import get_logger

from uuid import UUID

from app.db.models.document import Document

from app.schemas.document import DocumentResponse

from app.enums.document import DocumentStatus

from app.db.models.outbox_event import OutboxEvent

from fastapi import UploadFile

from app.uow.unit_of_work import UnitOfWork

from app.enums.outbox import EventType

from app.parser.base import ParserService


logger = get_logger()


class DocumentService:
    def __init__(
        self,
        uow: UnitOfWork,
        storage: StorageService,
        parser: ParserService,
    ):
        self.uow = uow
        self.storage = storage
        self.parser = parser

    def upload_document(
        self,
        file: UploadFile,
        user_id: UUID,
    ) -> DocumentResponse:

        storage_result = self.storage.store(file)

        try:
            document = Document(
                user_id=user_id,
                original_filename=file.filename,
                storage_key=storage_result.storage_key,
                content_type=file.content_type,
                file_size=storage_result.size,
                status=DocumentStatus.UPLOADED,
            )

            event = OutboxEvent(
                event_type=EventType.DOCUMENT_UPLOADED,
                payload={
                    "document_id": str(document.id),
                },
            )

            self.uow.documents.create(document)
            self.uow.outbox.create(event)

            self.uow.commit()

        except Exception:
            self.uow.rollback()
            try:
                self.storage.delete(storage_result.storage_key)
            except Exception:
                logger.exception(
                    "Failed to cleanup uploaded file after transaction rollback."
                )

            raise

        return DocumentResponse(
            id=document.id,
            filename=document.original_filename,
            file_size=document.file_size,
            status=document.status,
            created_at=document.created_at,
        )
