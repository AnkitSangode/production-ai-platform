import json
from typing import Any
from uuid import UUID

import aio_pika
from aio_pika import (
    Channel,
    Connection,
    DeliveryMode,
    Exchange,
    Message,
)
from aio_pika.abc import AbstractQueue

from app.core.config import Settings
from app.enums.outbox import EventType
from app.messaging.base import (
    BrokerConnectionError,
    MessageBroker,
    MessagePublishError,
)
from app.messaging.topology import BrokerTopology


class RabbitMQBroker(MessageBroker):

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

    async def connect(self) -> None:
        try:
            self.connection = await aio_pika.connect_robust(
                self.settings.rabbitmq_url,
            )

            self.channel = await self.connection.channel(
                publisher_confirms=True,
            )

        except Exception as exc:
            self.connection = None
            self.channel = None
            self.exchange = None

            raise BrokerConnectionError("Failed to connect to RabbitMQ.") from exc

    async def setup_exchange(self) -> None:

        if self.channel is None:
            raise BrokerConnectionError("RabbitMQ broker is not connected.")

        topology = BrokerTopology(self.channel)

        try:
            self.exchange = await topology.declare_exchange(
                exchange_name=self.exchange_name,
            )

        except Exception as exc:
            raise BrokerConnectionError("Failed to declare RabbitMQ exchange.") from exc

    async def setup_consumer_topology(
        self,
        *,
        queue_name: str,
        event_type: EventType,
    ) -> AbstractQueue:

        if self.channel is None:
            raise BrokerConnectionError("RabbitMQ broker is not connected.")

        if self.exchange is None:
            raise BrokerConnectionError("RabbitMQ exchange is not configured.")

        topology = BrokerTopology(self.channel)

        try:
            # 1. Declare dead-letter exchange
            dead_letter_exchange = await topology.declare_dead_letter_exchange(
                exchange_name=self.settings.rabbitmq_dlq_exchange,
            )

            # 2. Declare dead-letter queue and bind it
            await topology.declare_dead_letter_queue(
                queue_name=self.settings.rabbitmq_document_dlq,
                exchange=dead_letter_exchange,
                routing_key="dead-letter",
            )

            # 3. Declare processing queue
            queue = await topology.declare_processing_queue(
                queue_name=queue_name,
                dead_letter_exchange=self.settings.rabbitmq_dlq_exchange,
                dead_letter_routing_key="dead-letter",
            )

            # 4. Bind processing queue to main exchange
            await topology.bind_queue(
                queue=queue,
                exchange=self.exchange,
                routing_key=event_type.value,
            )

        # except Exception as exc:
        #     print(f"Consumer topology error: {exc!r}")

        #     raise BrokerConnectionError(
        #         "Failed to configure consumer topology."
        #     ) from exc

        except Exception as exc:
            print("\n========== CONSUMER TOPOLOGY ERROR ==========")
            print(type(exc).__name__)
            print(str(exc))
            print("=============================================\n")

            raise

        return queue

    @property
    def is_connected(self) -> bool:
        return (
            self.connection is not None
            and not self.connection.is_closed
            and self.channel is not None
            and not self.channel.is_closed
        )

    @property
    def is_ready(self) -> bool:
        return self.is_connected and self.exchange is not None

    async def publish(
        self,
        *,
        message_id: UUID,
        event_type: EventType,
        payload: dict[str, Any],
    ) -> None:

        if not self.is_ready:
            raise BrokerConnectionError("RabbitMQ broker is not ready.")

        body = json.dumps(
            {
                "message_id": str(message_id),
                "event_type": event_type.value,
                "payload": payload,
            }
        ).encode("utf-8")

        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        try:
            assert self.exchange is not None

            await self.exchange.publish(
                message,
                routing_key=event_type.value,
            )

        except (
            aio_pika.exceptions.AMQPConnectionError,
            aio_pika.exceptions.AMQPChannelError,
            aio_pika.exceptions.ChannelInvalidStateError,
        ) as exc:

            raise BrokerConnectionError(
                "RabbitMQ connection or channel became unavailable."
            ) from exc

        except aio_pika.exceptions.PublishError as exc:

            raise MessagePublishError(
                f"RabbitMQ rejected message {message_id}."
            ) from exc

    async def close(self) -> None:

        if self.connection is not None:

            try:
                await self.connection.close()

            finally:
                self.connection = None
                self.channel = None
                self.exchange = None
