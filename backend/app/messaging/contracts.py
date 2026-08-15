from dataclasses import dataclass
from typing import Any
from uuid import UUID
from app.enums.outbox import EventType

@dataclass(frozen=True)
class ClaimedOutboxMessage:
    """
    Immutable representation of a claimed outbox event.

    We intentionally don't pass SQLAlchemy ORM objects
    into RabbitMQ-related code.
    """

    event_id: UUID
    event_type: EventType
    payload: dict[str, Any]
    worker_id: str
