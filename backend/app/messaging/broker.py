from typing import Protocol, Any

from collections.abc import Awaitable, Callable

from app.messaging.messages import Message

MessageHandler = Callable[
    [Message],
    Awaitable[None],
]



class MessageBroker(Protocol):

    async def connect(self) -> None:
        ...
    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish an event to the message broker."""
        ...
    async def consume(
        self,
        queue_name: str,
        handler: MessageHandler,
    ) -> None:
        ...
