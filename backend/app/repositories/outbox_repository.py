from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.db.models.outbox_event import OutboxEvent

from app.messaging.outbox_publisher import ClaimedOutboxMessage


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

        Eligible events:
        - have not been published
        - have not exceeded the retry limit
        - are either unclaimed or have an expired lease

        This method:
        - locks eligible rows
        - skips rows locked by another publisher
        - assigns worker ownership
        - assigns a lease expiration

        This method does NOT commit.
        The caller owns the transaction boundary.
        """

        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.published_at.is_(None)
            )
            .where(
                OutboxEvent.retry_count < max_retry_count
            )
            .where(
                or_(
                    OutboxEvent.worker_id.is_(None),
                    OutboxEvent.lease_expires_at <= now,
                )
            )
            .order_by(
                OutboxEvent.created_at
            )
            .limit(batch_size)
            .with_for_update(
                skip_locked=True
            )
        )

        events = list(
            self.db.scalars(stmt)
        )

        messages: list[ClaimedOutboxMessage] = []

        for event in events:
            event.claim(
                worker_id=worker_id,
                lease_expires_at=lease_expires_at,
            )

             # 2. Extract the data needed after the session closes
            messages.append(
                ClaimedOutboxMessage(
                    event_id=event.id,
                    event_type=event.event_type,
                    payload=event.payload,
                    worker_id=worker_id,
                )
            )

        return events

    def mark_published(
        self,
        *,
        event_id: UUID,
        worker_id: str,
        published_at: datetime,
    ) -> bool:
        """
        Mark an event as published only if this worker
        still owns the event.

        Returns True if the event was updated.
        Returns False if the worker no longer owns it
        or the event was already published.
        """

        stmt = (
            update(OutboxEvent)
            .where(
                OutboxEvent.id == event_id
            )
            .where(
                OutboxEvent.worker_id == worker_id
            )
            .where(
                OutboxEvent.published_at.is_(None)
            )
            .values(
                published_at=published_at,
                worker_id=None,
                lease_expires_at=None,
            )
        )

        result = self.db.execute(stmt)

        return result.rowcount == 1

    def mark_failed(
        self,
        *,
        event_id: UUID,
        worker_id: str,
    ) -> bool:
        """
        Release an event owned by this worker and
        increment its retry count.

        Returns True if the event was updated.
        Returns False if the worker no longer owns
        the event or the event was already published.
        """

        stmt = (
            update(OutboxEvent)
            .where(
                OutboxEvent.id == event_id
            )
            .where(
                OutboxEvent.worker_id == worker_id
            )
            .where(
                OutboxEvent.published_at.is_(None)
            )
            .values(
                retry_count=OutboxEvent.retry_count + 1,
                worker_id=None,
                lease_expires_at=None,
            )
        )

        result = self.db.execute(stmt)

        return result.rowcount == 1

    def get_by_id(
        self,
        event_id: UUID,
    ) -> OutboxEvent | None:
        """
        Retrieve an OutboxEvent by ID.
        """
        return self.db.get(
            OutboxEvent,
            event_id,
        )