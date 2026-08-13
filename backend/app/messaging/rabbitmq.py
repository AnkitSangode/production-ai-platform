import json
from typing import Any
from uuid import UUID

import aio_pika
from aio_pika import (
    Channel,
    Connection,
    DeliveryMode,
    Exchange,
    ExchangeType,
    Message,
)

from app.core.config import Settings
from app.messaging.base import (
    BrokerConnectionError,
    MessageBroker,
    MessagePublishError,
)


class RabbitMQBroker(MessageBroker):
    """
    RabbitMQ implementation of MessageBroker.

    Responsibilities:
    - RabbitMQ connection lifecycle
    - Channel lifecycle
    - Exchange lifecycle
    - Message publishing
    - RabbitMQ-specific error translation

    Does NOT:
    - access PostgreSQL
    - know about OutboxEvent
    - manage event retries
    - manage leases
    - mark events as published
    """

    def __init__(
        self,
        settings: Settings,
        exchange_name: str,
    ) -> None:
        self.settings = settings
        self.exchange_name = exchange_name

        self.connection: Connection | None = None
        self.channel: Channel | None = None
        self.exchange: Exchange | None = None

    @property
    def is_ready(self) -> bool:
        """
        Return whether the broker currently has an
        initialized connection, channel, and exchange.
        """

        if self.connection is None or self.channel is None or self.exchange is None:
            return False

        if self.connection.is_closed:
            return False

        if self.channel.is_closed:
            return False

        return True

    async def connect(self) -> None:
        """
        Establish a robust RabbitMQ connection.

        Connection
            ↓
        Channel
            ↓
        Durable Topic Exchange
        """

        if self.is_ready:
            return

        await self._reset_connection()

        try:
            self.connection = await aio_pika.connect_robust(
                self.settings.rabbitmq_url,
            )

            self.channel = await self.connection.channel(
                publisher_confirms=True,
            )

            self.exchange = await self.channel.declare_exchange(
                name=self.exchange_name,
                type=ExchangeType.TOPIC,
                durable=True,
            )

        except Exception as exc:
            await self._reset_connection()

            raise BrokerConnectionError("Failed to connect to RabbitMQ.") from exc

    async def wait_until_ready(self) -> None:
        """
        Wait for an established robust channel to become ready.

        This is used after a connection interruption.

        It does not create a new connection.
        """

        if self.connection is None:
            raise BrokerConnectionError("RabbitMQ has not been connected.")

        if self.channel is None:
            raise BrokerConnectionError("RabbitMQ channel has not been created.")

        try:
            await self.channel.ready()

        except Exception as exc:
            raise BrokerConnectionError("RabbitMQ channel failed to recover.") from exc

    async def publish(
        self,
        *,
        message_id: UUID,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Publish one persistent message.

        Publisher confirms are enabled on the channel.
        """

        self._require_connected()

        body = json.dumps(
            {
                "event_id": str(message_id),
                "event_type": event_type,
                "payload": payload,
            }
        ).encode("utf-8")

        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=str(message_id),
        )

        assert self.exchange is not None

        try:
            await self.exchange.publish(
                message,
                routing_key=event_type,
            )

        except (
            aio_pika.exceptions.AMQPConnectionError,
            ConnectionError,
            TimeoutError,
        ) as exc:

            raise BrokerConnectionError(
                "RabbitMQ connection failed during publication."
            ) from exc

        except Exception as exc:

            raise MessagePublishError(
                "RabbitMQ failed to publish the message."
            ) from exc

    async def close(self) -> None:
        """
        Close the RabbitMQ connection.
        """

        await self._reset_connection()

    def _require_connected(self) -> None:
        """
        Ensure RabbitMQ is initialized before publishing.
        """

        if not self.is_ready:
            raise BrokerConnectionError("RabbitMQ broker is not ready.")

    async def _reset_connection(self) -> None:
        """
        Clear local RabbitMQ state and close the
        existing connection if one exists.
        """

        connection = self.connection

        self.connection = None
        self.channel = None
        self.exchange = None

        if connection is not None:
            try:
                await connection.close()
            except Exception:
                pass
