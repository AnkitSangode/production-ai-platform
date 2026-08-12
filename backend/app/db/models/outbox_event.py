from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.enums.outbox import EventType


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    # -------------------------
    # Identity
    # -------------------------

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # -------------------------
    # Event
    # -------------------------

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType),
        nullable=False,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    # -------------------------
    # Publication
    # -------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------
    # Processing
    # -------------------------

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    worker_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------
    # Publication behavior
    # -------------------------

    def mark_published(
        self,
        *,
        published_at: datetime,
    ) -> None:
        """Mark the event as successfully published."""
        self.published_at = published_at

    # -------------------------
    # Processing-worker behavior
    # -------------------------

    def claim(
        self,
        *,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> None:
        """Claim this event for processing by a worker."""
        self.worker_id = worker_id
        self.lease_expires_at = lease_expires_at

    def release_lease(self) -> None:
        """Release the processing lease."""
        self.worker_id = None
        self.lease_expires_at = None

    def mark_processing_failed(self) -> None:
        """Record a processing failure and release the worker lease."""
        self.retry_count += 1
        self.release_lease()