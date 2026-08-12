from abc import ABC, abstractmethod
from uuid import UUID


class MessageBroker(ABC):

    @abstractmethod
    async def connect(self) -> None:
        """Establish a connection to the message broker."""
        ...

    @abstractmethod
    async def publish(
        self,
        *,
        message_id: UUID,
        event_type: str,
        payload: dict,
    ) -> None:
        """Publish a message to the broker."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the broker connection."""
        ...