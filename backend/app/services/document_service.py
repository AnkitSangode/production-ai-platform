from sqlalchemy.orm import Session

from app.storage.local import StorageService

from app.core.logging import get_logger

from uuid import UUID

from app.exceptions.storage import StorageLimitExceededError

from app.db.models.document import Document

from app.db.models.outbox_event import OutboxEvent

from app.enums.document import DocumentStatus

from app.enums.outbox import EventType

from app.schemas.document import DocumentResponse

from app.enums.document import DocumentContentType

from fastapi import UploadFile

from app.uow.unit_of_work import UnitOfWork


from app.parser.base import ParserService

from app.core.config import Settings


from app.exceptions.document import (
    DocumentTooLargeError,
    EmptyFileError,
    UnsupportedFileTypeError,
    DocumentNotFoundError,
)

logger = get_logger(__name__)


class DocumentService:
    def __init__(
        self,
        uow: UnitOfWork,
        storage: StorageService,
        parser: ParserService,
        settings: Settings,
    ):
        self.uow = uow
        self.storage = storage
        self.parser = parser
        self.settings = settings

    def upload_document(
        self,
        file: UploadFile,
        user_id: UUID,
    ) -> DocumentResponse:

        if file.size == 0:
            raise EmptyFileError()

        if file.size is not None and file.size > self.settings.MAX_DOCUMENT_SIZE:
            raise DocumentTooLargeError(
                actual_size=file.size,
                max_size=self.settings.MAX_DOCUMENT_SIZE,
            )

        if file.content_type not in DocumentContentType.values():
            raise UnsupportedFileTypeError()

        try:
            storage_result = self.storage.store(file)
        except StorageLimitExceededError as exc:
            raise DocumentTooLargeError(
                actual_size=exc.actual_size,
                max_size=exc.max_size,
            ) from exc

        try:
            document = Document(
                user_id=user_id,
                original_filename=file.filename,
                storage_key=storage_result.storage_key,
                content_type=file.content_type,
                file_size=storage_result.file_size,
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

    def get_document(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> Document:

        document = self.uow.documents.get_by_id(document_id)

        if document is None or document.user_id != user_id:
            raise DocumentNotFoundError()

        return document

    def delete_document(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> None:

        document = self.uow.documents.get_by_id(document_id)

        if document is None or document.user_id != user_id:
            raise DocumentNotFoundError()

        self.uow.documents.delete(document)
        self.uow.commit()

    def update_document(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> Document:

        document = self.uow.documents.get_by_id(document_id)

        if document is None or document.user_id != user_id:
            raise DocumentNotFoundError()

        # perform allowed updates

        self.uow.commit()

        return document
