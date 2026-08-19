from collections.abc import Awaitable, Callable

from aio_pika import IncomingMessage
from aio_pika.abc import AbstractQueue

from app.messaging.errors import (
    PermanentError,
    RetryableError,
)
from app.messaging.rabbitmq_message import (
    InvalidRabbitMQMessage,
    RabbitMQMessage,
)
from app.messaging.retry_policy import RetryPolicy

MessageHandler = Callable[
    [RabbitMQMessage],
    Awaitable[None],
]


class RabbitMQConsumer:

    def __init__(
        self,
        queue: AbstractQueue,
        handler: MessageHandler,
        retry_policy: RetryPolicy,
    ) -> None:
        self.queue = queue
        self.handler = handler
        self.retry_policy = retry_policy

    async def start(self) -> None:
        await self.queue.consume(
            self._handle_message,
        )

    async def _handle_message(
        self,
        message: IncomingMessage,
    ) -> None:

        # print("\n========== RABBITMQ DELIVERY ==========")
        # print(f"redelivered: {message.redelivered}")
        # print(f"headers: {message.headers}")
        # print("=======================================\n")

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

        except RetryableError:

            if self.retry_policy.should_retry(
                acquired_count=application_message.acquired_count,
            ):
                await application_message.nack(
                    requeue=True,
                )
            else:
                await application_message.reject(
                    requeue=False,
                )

        except PermanentError:

            await application_message.reject(
                requeue=False,
            )

        except Exception:

            await application_message.nack(
                requeue=True,
            )

        else:

            await application_message.ack()
