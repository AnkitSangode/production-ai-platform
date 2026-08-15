from collections.abc import Awaitable, Callable

from aio_pika import IncomingMessage
from aio_pika.abc import AbstractQueue

from app.messaging.messages import Message
from app.messaging.rabbitmq_message import (
    InvalidRabbitMQMessage,
    RabbitMQMessage,
)

MessageHandler = Callable[
    [Message],
    Awaitable[None],
]


class RabbitMQConsumer:

    def __init__(
        self,
        queue: AbstractQueue,
        handler: MessageHandler,
    ) -> None:
        self.queue = queue
        self.handler = handler

    async def start(self) -> None:
        await self.queue.consume(
            self._handle_message,
        )

    async def _handle_message(
        self,
        message: IncomingMessage,
    ) -> None:

        try:
            application_message = RabbitMQMessage(
                message,
            )

        except InvalidRabbitMQMessage:
            await message.reject(
                requeue=False,
            )
            return

        try:
            await self.handler(
                application_message,
            )

            await application_message.ack()

        except Exception:
            await application_message.nack(
                requeue=True,
            )
