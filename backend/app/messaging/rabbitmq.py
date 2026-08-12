import aio_pika

from aio_pika import Connection, Channel, ExchangeType, Exchange, IncomingMessage

from app.messaging.broker import MessageBroker, MessageHandler

from uuid import UUID

from app.core.config import Settings

import json

from aio_pika import Message, DeliveryMode

from app.messaging.messages import Messages

from typing import Any

from app.messaging.exceptions import InvalidMessageError


class RabbitMQMessageBroker(MessageBroker):
    """
    RabbitMQ implementation of the MessageBroker interface.

    This class is responsible for:
    - maintaining the RabbitMQ connection
    - maintaining the publishing channel
    - declaring the event exchange
    - publishing persistent messages
    - waiting for publisher confirmation
    """

    EXCHANGE_NAME = "atlas.events"

    def __init__(
        self,
        settings: Settings,
        exchange_name: str = EXCHANGE_NAME,
    ) -> None:
        self.settings = settings
        self.exchange_name = exchange_name

        self.connection: aio_pika.abc.AbstractRobustConnection | None = None

        self.channel: aio_pika.abc.AbstractRobustChannel | None = None

        self.exchange: aio_pika.abc.AbstractRobustExchange | None = None

    async def connect(self) -> None:
        """
        Establish the RabbitMQ connection and declare
        the event exchange.
        """

        self.connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)

        self.channel = await self.connection.channel(
            publisher_confirms=True,
        )

        self.exchange = await self.channel.declare_exchange(
            name=self.exchange_name,
            type=ExchangeType.TOPIC,
            durable=True,
        )

    def _require_connected(self) -> None:
        """
        Ensure the broker has been connected before
        performing broker operations.
        """

        if self.connection is None or self.channel is None or self.exchange is None:
            raise RuntimeError(
                "RabbitMQ broker is not connected. "
                "Call 'connect()' before using the broker."
            )

    def _get_routing_key(
        self,
        event_type: str,
    ) -> str:
        """
        Convert an application event type into
        its RabbitMQ routing key.
        """

        routing_keys = {
            "DOCUMENT_UPLOADED": "document.uploaded",
        }

        try:
            return routing_keys[event_type]
        except KeyError:
            raise ValueError(f"Unsupported event type: {event_type}") from None

    async def publish(
        self,
        *,
        message_id: UUID,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Publish a persistent event to RabbitMQ.

        The method returns only after RabbitMQ confirms
        the publication when publisher confirms are enabled.
        """

        self._require_connected()

        routing_key = self._get_routing_key(event_type)

        body = json.dumps(
            {
                "message_id": str(message_id),
                "event_type": event_type,
                "payload": payload,
            }
        ).encode("utf-8")

        message = Message(
            body=body,
            message_id=str(message_id),
            type=event_type,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        assert self.exchange is not None

        await self.exchange.publish(
            message=message,
            routing_key=routing_key,
        )

    async def close(self) -> None:
        """Close the RabbitMQ connection."""

        if self.connection is not None:
            await self.connection.close()

        self.connection = None
        self.channel = None
        self.exchange = None

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

        self.logger.info(
            "Consuming messages from queue '%s' with routing key '%s'",
            queue_name,
            routing_key,
        )

        async with queue.iterator() as iterator:
            async for incoming_message in iterator:

                try:
                    message = RabbitMQMessage(
                        incoming_message=incoming_message,
                    )

                except InvalidMessageError:

                    self.logger.exception("Received invalid RabbitMQ message.")

                    await incoming_message.reject(
                        requeue=False,
                    )

                    continue

                await handler(message)


class RabbitMQMessage(Messages):

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
