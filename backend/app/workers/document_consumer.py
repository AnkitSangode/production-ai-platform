import asyncio

from app.core.config import get_settings
from app.enums.outbox import EventType
from app.messaging.rabbitmq import RabbitMQBroker
from app.messaging.rabbitmq_consumer import RabbitMQConsumer
from app.messaging.rabbitmq_message import RabbitMQMessage


async def test_handler(
    message: RabbitMQMessage,
) -> None:
    print(
        f"Received event: "
        f"{message.event_type} "
        f"({message.message_id})"
    )

    print(f"Payload: {message.payload}")


async def main() -> None:

    settings = get_settings()

    broker = RabbitMQBroker(
        settings=settings,
        exchange_name=settings.rabbitmq_exchange,
    )

    try:
        await broker.connect()
        await broker.setup_exchange()

        queue = await broker.setup_consumer_topology(
            queue_name=settings.rabbitmq_document_queue,
            event_type=EventType.DOCUMENT_UPLOADED,
        )

        consumer = RabbitMQConsumer(
            queue=queue,
            handler=test_handler,
        )

        await consumer.start()

        print(
            "Document consumer started. "
            "Waiting for messages..."
        )

        await asyncio.Future()

    finally:
        await broker.close()


if __name__ == "__main__":
    asyncio.run(main())