from logging import Logger

from app.messaging.broker import MessageBroker
from app.messaging.messages import Message


class DocumentConsumer:
    """
    Coordinates message consumption.

    Responsibilities:
    - Register a message handler with the broker.
    - Receive messages from the broker.
    - Delegate business logic to the processing service.
    - ACK/NACK messages based on processing outcome.
    """

    def __init__(
        self,
        broker: MessageBroker,
        logger: Logger,
        queue_name: str,
    ) -> None:
        self.broker = broker
        self.logger = logger
        self.queue_name = queue_name

    async def start(self) -> None:
        """
        Starts consuming messages from the configured queue.
        """

        self.logger.info(
            "Starting document consumer for queue '%s'",
            self.queue_name,
        )

        await self.broker.consume(
            queue_name=self.queue_name,
            handler=self.handle,
        )

    async def handle(
        self,
        message: Message,
    ) -> None:
        """
        Handles a single message received from RabbitMQ.

        TODO (Sprint 2):
        - Extract document_id
        - Call DocumentProcessingService
        - ACK on success
        - NACK on temporary failures
        - Reject on permanent failures
        """

        self.logger.info(
            "Received message: %s",
            message,
        )