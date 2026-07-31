import asyncio

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.messaging.rabbitmq import RabbitMQBroker
from app.messaging.exchanges import DOCUMENT_EXCHANGE
from app.messaging.queues import DOCUMENT_UPLOAD_QUEUE
from app.messaging.messages import DOCUMENT_UPLOADED
from app.messaging.consumer import DocumentConsumer


async def main() -> None:
    settings = get_settings()

    configure_logging()
    logger = get_logger(__name__)

    broker = RabbitMQBroker(
        settings=settings,
        exchange_name=DOCUMENT_EXCHANGE,
        logger=logger,
    )

    consumer = DocumentConsumer(
        broker=broker,
        logger=logger,
        queue_name=DOCUMENT_UPLOAD_QUEUE,
        routing_key=DOCUMENT_UPLOADED,
    )

    logger.info("Starting document worker...")

    await broker.connect()

    await consumer.start()


if __name__ == "__main__":
    asyncio.run(main())