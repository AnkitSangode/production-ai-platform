from typing import Any, Protocol
from uuid import UUID

from app.enums.outbox import EventType


class Message(Protocol):

    @property
    def message_id(self) -> UUID: ...

    @property
    def event_type(self) -> EventType: ...

    @property
    def payload(self) -> dict[str, Any]: ...

    async def ack(self) -> None: ...

    async def nack(
        self,
        requeue: bool = True,
    ) -> None: ...

    async def reject(
        self,
        requeue: bool = False,
    ) -> None: ...
