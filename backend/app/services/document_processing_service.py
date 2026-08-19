from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.uow.unit_of_work import UnitOfWork

logger = get_logger(__name__)


class DocumentProcessingService:
    def __init__(
        self,
        uow: UnitOfWork,
        worker_id: UUID,
    ):
        self.uow = uow
        self.worker_id = worker_id

    def process_document(
        self,
        *,
        document_id: UUID,
    ) -> bool:

        lease_duration = timedelta(minutes=5)

        lease_expiry = datetime.now(timezone.utc) + lease_duration

        claimed = self.uow.documents.claim_for_processing(
            document_id=document_id,
            worker_id=self.worker_id,
            lease_expiry=lease_expiry,
        )

        if not claimed:
            logger.info(
                "Document is already owned by another worker.",
                extra={
                    "document_id": str(document_id),
                },
            )
            return False

        logger.info(
            "Document claimed for processing.",
            extra={
                "document_id": str(document_id),
                "worker_id": str(self.worker_id),
            },
        )

        self.uow.commit()

        return True
