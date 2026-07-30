
from typing import Any, Protocol


class Message(Protocol):
    @property
    def event_type(self) -> str:
        ...

    @property
    def payload(self) -> dict[str, Any]:
        ...

    async def ack(self) -> None:
        ...

    async def nack(
        self,
        requeue: bool = True,
    ) -> None:
        ...

    async def reject(
        self,
        requeue: bool = False,
    ) -> None:
        ...