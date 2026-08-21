from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.uow.unit_of_work import UnitOfWork
from app.messaging.errors import RetryableError, PermanentError
from app.enums.document import DocumentClaimResult,DocumentProcessingStage


logger = get_logger(__name__)


class DocumentProcessingService:
    def __init__(
        self,
        uow: UnitOfWork,
        worker_id: UUID,
    ):
        self.uow = uow
        self.worker_id = worker_id

    # def _process(self, document_id: UUID) -> None:
    #     """Process the document.

    #     Real parsing, chunking, embedding, and indexing
    #     will be implemented later.
    #     """
    #     pass

    def _process(
        self,
        document_id: UUID,
    ) -> None:
        raise RetryableError(
        "Simulated retryable processing failure."
    )

    def process_document(self, *, document_id: UUID, final_attempt: bool) -> bool:

        print("P1: Entered process_document")
        print(f"P2: final_attempt={final_attempt}")

        lease_duration = timedelta(minutes=5)

        lease_expiry = datetime.now(timezone.utc) + lease_duration

        print("P3: Calling claim_for_processing")

        claim_result = self.uow.documents.claim_for_processing(
            document_id=document_id,
            worker_id=self.worker_id,
            lease_expiry=lease_expiry,
        )

        print(f"P4: claim_result={claim_result}")

        if claim_result == DocumentClaimResult.CLAIMED:

            print("P5: Claim succeeded, committing...")

            self.uow.commit()

            print("P6: Claim commit completed")

            updated = self.uow.documents.update_processing_stage(
                document_id=document_id,
                worker_id=self.worker_id,
                stage=DocumentProcessingStage.PARSING,
            )

            if not updated:
                raise RuntimeError(
                    "Document ownership was lost before parsing."
                )

            self.uow.commit()

            logger.info(
                "Document claimed for processing.",
                extra={
                    "document_id": str(document_id),
                    "worker_id": str(self.worker_id),
                },
            )

            print("P7: Claim log completed")

        elif claim_result == DocumentClaimResult.ALREADY_OWNED:
            logger.info(
                "Document already owned by this worker; continuing processing.",
                extra={
                    "document_id": str(document_id),
                    "worker_id": str(self.worker_id),
                },
            )

        try:
            print("P8: Calling _process()")
            self._process(document_id)
            print("P9: _process() returned")

            # 4. Mark READY
            completed = self.uow.documents.complete_processing(
                document_id=document_id,
                worker_id=self.worker_id,
            )

            if not completed:
                raise RuntimeError("Document ownership was lost before completion.")

            logger.info(
                "Document processing completed.",
                extra={
                    "document_id": str(document_id),
                    "worker_id": str(self.worker_id),
                },
            )

            self.uow.commit()

        except PermanentError as exc:
            failed = self.uow.documents.fail_processing(
                document_id=document_id,
                worker_id=self.worker_id,
                error_message=str(exc),
            )

            if not failed:
                raise RuntimeError(
                    "Document ownership was lost before failure could be recorded."
                ) from exc

            self.uow.commit()

            raise

        except RetryableError as exc:

            if not final_attempt:
                raise

            failed = self.uow.documents.fail_processing(
                document_id=document_id,
                worker_id=self.worker_id,
                error_message=str(exc),
            )

            if not failed:
                raise RuntimeError(
                    "Document ownership was lost before final failure could be recorded."
                ) from exc

            self.uow.commit()

            raise
