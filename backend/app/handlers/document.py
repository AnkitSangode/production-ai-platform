from uuid import UUID

from app.messaging.rabbitmq_message import RabbitMQMessage
from app.services.document_processing_service import DocumentProcessingService
from app.uow.factory import create_unit_of_work


def get_document_id(
    message: RabbitMQMessage,
) -> UUID:

    if "document_id" not in message.payload:
        raise ValueError(
            "document_id is missing from the message payload."
        )

    try:
        return UUID(
            str(message.payload["document_id"])
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid document_id in message payload."
        ) from exc


async def handle_document_uploaded(
    message: RabbitMQMessage,
    worker_id: UUID,
) -> None:

    document_id = get_document_id(message)

    with create_unit_of_work() as uow:

        service = DocumentProcessingService(
            uow=uow,
            worker_id=worker_id,
        )

        service.process_document(
            document_id=document_id,
        )