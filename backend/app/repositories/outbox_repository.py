from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.outbox_event import OutboxEvent


class OutboxRepository:
    """Persistence operations for OutboxEvent."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, event: OutboxEvent) -> None:
        """
        Stage a new OutboxEvent for persistence.
        """
        self.db.add(event)

    def claim_batch(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_expires_at: datetime,
        batch_size: int,
        max_retry_count: int,
    ) -> list[OutboxEvent]:
        """
        Claim a batch of unpublished events.

        This method:
        - selects unpublished events
        - skips events currently leased by another worker
        - acquires row-level locks
        - assigns the lease to this worker

        NOTE:
        This method does NOT commit the transaction.
        The caller owns the transaction boundary.
        """

        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .where(OutboxEvent.retry_count < max_retry_count)
            .where(
                or_(
                    OutboxEvent.worker_id.is_(None),
                    OutboxEvent.lease_expires_at < now,
                )
            )
            .order_by(OutboxEvent.created_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )

        events = list(self.db.scalars(stmt))

        for event in events:
            event.claim(
                worker_id=worker_id,
                lease_expires_at=lease_expires_at,
            )

        return events

    def get_by_id(self, event_id: str) -> OutboxEvent | None:
        """
        Retrieve an OutboxEvent by its id.
        """
        return self.db.get(OutboxEvent, event_id)