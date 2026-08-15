import asyncio

from app.core.config import Settings
from app.messaging.outbox_publisher import OutboxPublisher
from app.messaging.rabbitmq import RabbitMQBroker
from app.uow.factory import create_unit_of_work


async def main() -> None:

    settings = Settings()

    broker = RabbitMQBroker(
        settings=settings,
        exchange_name=settings.rabbitmq_exchange,
    )

    await broker.connect()
    await broker.setup_exchange()

    publisher = OutboxPublisher(
        broker=broker,
        uow_factory=create_unit_of_work,
        batch_size=100,
        poll_interval=5.0,
        lease_seconds=60,
        max_retry_count=5,
    )

    try:
        await publisher.run_forever()
    finally:
        await broker.close()


if __name__ == "__main__":
    asyncio.run(main())