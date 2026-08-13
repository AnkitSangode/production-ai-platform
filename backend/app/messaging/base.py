# app/messaging/base.py

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class MessageBrokerError(Exception):
    """Base exception for message broker failures."""


class BrokerConnectionError(MessageBrokerError):
    """The broker connection is unavailable."""


class MessagePublishError(MessageBrokerError):
    """The broker definitively rejected a message."""


class MessageBroker(ABC):

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """Return whether the broker is ready for publishing."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Establish a connection to the broker."""
        ...

    @abstractmethod
    async def wait_until_ready(self) -> None:
        """
        Wait until the broker is ready for publishing.
        """
        ...

    @abstractmethod
    async def publish(
        self,
        *,
        message_id: UUID,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish a message to the broker."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the broker connection."""
        ...