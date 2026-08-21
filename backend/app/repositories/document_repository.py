from sqlalchemy.orm import Session
from app.db.models import Document
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, update
from app.enums.document import (
    DocumentStatus,
    DocumentClaimResult,
    DocumentProcessingStage,
)
from app.exceptions.document import DocumentNotFoundError


class DocumentRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, document: Document) -> Document:
        self.db.add(document)
        return document

    def claim_for_processing(
        self,
        *,
        document_id: UUID,
        worker_id: UUID,
        lease_expiry: datetime,
    ) -> DocumentClaimResult:

        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                or_(
                    Document.status == DocumentStatus.UPLOADED,
                    and_(
                        Document.status == DocumentStatus.PROCESSING,
                        Document.processing_lease_expiry <= func.now(),
                    ),
                ),
            )
            .values(
                processing_worker_id=worker_id,
                processing_lease_expiry=lease_expiry,
                status=DocumentStatus.PROCESSING,
            )
        )

        result = self.db.execute(statement)

        if result.rowcount == 1:
            return DocumentClaimResult.CLAIMED

        document = self.db.get(Document, document_id)
        if document is None:
            raise DocumentNotFoundError()

        if document.processing_worker_id == worker_id:
            return DocumentClaimResult.ALREADY_OWNED

        return DocumentClaimResult.OWNED_BY_OTHER

    def complete_processing(
        self,
        *,
        document_id: UUID,
        worker_id: UUID,
    ) -> bool:

        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.status == DocumentStatus.PROCESSING,
                Document.processing_worker_id == worker_id,
                Document.processing_lease_expiry > func.now(),
            )
            .values(
                status=DocumentStatus.READY,
                processing_worker_id=None,
                processing_lease_expiry=None,
            )
        )

        result = self.db.execute(statement)

        return result.rowcount == 1

    def fail_processing(
        self,
        *,
        document_id: UUID,
        worker_id: UUID,
        error_message: str,
    ) -> bool:

        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.status == DocumentStatus.PROCESSING,
                Document.processing_worker_id == worker_id,
                Document.processing_lease_expiry > func.now(),
            )
            .values(
                status=DocumentStatus.FAILED,
                processing_worker_id=None,
                processing_lease_expiry=None,
                error_message=error_message,
            )
        )

        result = self.db.execute(statement)

        return result.rowcount == 1



    def update_processing_stage(
        self,
        *,
        document_id: UUID,
        worker_id: UUID,
        stage: DocumentProcessingStage,
    ) -> bool:

        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.status == DocumentStatus.PROCESSING,
                Document.processing_worker_id == worker_id,
                Document.processing_lease_expiry > func.now(),
            )
            .values(
                processing_stage=stage,
            )
        )

        result = self.db.execute(statement)

        return result.rowcount == 1
