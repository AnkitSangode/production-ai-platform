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
from app.messaging.delivery_context import DeliveryContext
from app.handlers.document import handle_document_uploaded

MessageHandler = Callable[
    [RabbitMQMessage,DeliveryContext],
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

        print("\n========== RABBITMQ DELIVERY ==========")
        print(f"redelivered: {message.redelivered}")
        print(f"headers: {message.headers}")
        print("=======================================\n")

        try:
            print("1. Creating RabbitMQMessage")

            application_message = RabbitMQMessage(
                message,
            )
            print("2. RabbitMQMessage created")

        except InvalidRabbitMQMessage:
            await message.reject(
                requeue=False,
            )
            return
        print("3. Calculating retry policy")

        should_retry = self.retry_policy.should_retry(
            acquired_count=application_message.acquired_count,
        )

        print(f"4. should_retry={should_retry}")

        context = DeliveryContext(
            final_attempt=not should_retry,
        )

        print(
            f"5. DeliveryContext created: "
            f"final_attempt={context.final_attempt}"
        )

        print("6. Calling handler")

        try:
            await self.handler(application_message, context)

            print("7. Handler returned successfully")

        except RetryableError:
            print("========== RETRYABLE ERROR CAUGHT ==========")
            print(f"document_id={application_message.payload.get('document_id')}")
            print(f"acquired_count={application_message.acquired_count}")
            print("============================================")

            print(f"should_retry={should_retry}")

            if should_retry:
                print("Calling NACK with requeue=True")

                await application_message.nack(
                    requeue=True,
                )

                print("NACK completed")

            else:
                print("Retry limit reached - rejecting message")

                await application_message.reject(
                    requeue=False,
                )

                print("Reject completed")
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
