import aio_pika

from aio_pika import Connection, Channel, ExchangeType, Exchange, IncomingMessage

from app.messaging.broker import MessageBroker

from app.core.config import Settings

import json

from aio_pika import Message, DeliveryMode

from typing import Any

from app.messaging.exceptions import InvalidMessageError

class RabbitMQBroker(MessageBroker):

    def __init__(self, settings: Settings, exchange_name: str) -> None:
        self.settings = settings
        self.exchange_name = exchange_name

        self.connection: Connection | None = None
        self.channel: Channel | None = None
        self.exchange: Exchange | None = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)

        self.channel = await self.connection.channel()

        self.exchange = await self.channel.declare_exchange(
            name=self.exchange_name,
            type=ExchangeType.TOPIC,
            durable=True,
        )

    def _require_connected(self) -> None:
        if self.connection is None or self.channel is None or self.exchange is None:
            raise RuntimeError(
                "RabbitMQ broker is not connected. "
                "Call 'connect()' before using the broker."
            )

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self._require_connected()

        body = json.dumps(payload).encode("utf-8")

        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        assert self.exchange is not None

        await self.exchange.publish(
            message=message,
            routing_key=event_type,
        )

    async def consume(
        self,
        queue_name: str,
        routing_key: str,
        handler: MessageHandler,
    ) -> None:
        self._require_connected()

        assert self.channel is not None
        assert self.exchange is not None

        queue = await self.channel.declare_queue(
            name=queue_name,
            durable=True,
        )

        await queue.bind(
            exchange=self.exchange,
            routing_key=routing_key,
        )

        async with queue.iterator() as iterator:

            async for incoming_message in iterator:

                try:
                    message = RabbitMQMessage(
                        incoming_message,
                    )

                except InvalidMessageError:

                    self.logger.exception(
                        "Invalid message received."
                    )

                    await incoming_message.reject(
                        requeue=False,
                    )

                    continue

                await handler(message)


class RabbitMQMessage(Message):

    def __init__(
        self,
        incoming_message: IncomingMessage,
    ) -> None:
        self._incoming_message = incoming_message

        body = json.loads(incoming_message.body.decode("utf-8"))

        self._event_type = body["event_type"]
        self._payload = body["payload"]

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def payload(self) -> dict[str, Any]:
        return self._payload

    async def ack(self) -> None:
        await self._incoming_message.ack()

    async def nack(
        self,
        requeue: bool = True,
    ) -> None:
        await self._incoming_message.nack(
            requeue=requeue,
        )

    async def reject(
        self,
        requeue: bool = False,
    ) -> None:
        await self._incoming_message.reject(
            requeue=requeue,
        )
