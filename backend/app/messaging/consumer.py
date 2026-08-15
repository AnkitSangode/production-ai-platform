from abc import ABC, abstractmethod
from typing import Any


class MessageConsumer(ABC):

    @abstractmethod
    async def start(self) -> None:
        """Start consuming messages."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop consuming messages."""
        ...