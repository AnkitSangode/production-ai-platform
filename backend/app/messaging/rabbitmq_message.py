import json
from typing import Any
from uuid import UUID

from aio_pika import IncomingMessage

from app.enums.outbox import EventType


class InvalidRabbitMQMessage(ValueError):
    """The RabbitMQ message cannot be converted into an application message."""


class RabbitMQMessage:

    def __init__(
        self,
        message: IncomingMessage,
    ) -> None:
        self._message = message

        try:
            data: dict[str, Any] = json.loads(message.body.decode("utf-8"))

            self._message_id = UUID(data["message_id"])

            self._event_type = EventType(data["event_type"])

            payload = data["payload"]

            if not isinstance(payload, dict):
                raise ValueError("Message payload must be a dictionary.")

            self._payload = payload

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise InvalidRabbitMQMessage("Invalid RabbitMQ message.") from exc

    @property
    def message_id(self) -> UUID:
        return self._message_id

    @property
    def event_type(self) -> EventType:
        return self._event_type

    @property
    def payload(self) -> dict[str, Any]:
        return self._payload

    @property
    def acquired_count(self) -> int:
        value = self._message.headers.get(
            "x-acquired-count",
            0,
        )

        if not isinstance(value, int):
            raise InvalidRabbitMQMessage(
                "Invalid x-acquired-count header."
            )

        return value

    async def ack(self) -> None:
        await self._message.ack()

    async def nack(
        self,
        requeue: bool = True,
    ) -> None:
        await self._message.nack(
            requeue=requeue,
        )

    async def reject(
        self,
        requeue: bool = False,
    ) -> None:
        await self._message.reject(
            requeue=requeue,
        )
