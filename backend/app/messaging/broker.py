from typing import Protocol, Any



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

