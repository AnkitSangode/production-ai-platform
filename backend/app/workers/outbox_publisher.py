import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import OutboxEvent
from app.messaging.broker import MessageBroker


class OutboxPublisher:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        broker: MessageBroker,
        worker_id: str,
        logger: logging.Logger,
        batch_size: int = 100,
        lease_duration: timedelta = timedelta(minutes=5),
        poll_interval: timedelta = timedelta(seconds=5),
        max_retry_count: int = 10,
    ):
        self.session_factory = session_factory
        self.broker = broker
        self.worker_id = worker_id
        self.logger = logger

        self.batch_size = batch_size
        self.lease_duration = lease_duration
        self.poll_interval = poll_interval
        self.max_retry_count = max_retry_count

    async def run(self) -> None:
        await self.broker.connect()

        self.logger.info("Outbox publisher started.")

        while True:
            session = self.session_factory()

            try:
                await self.process_batch(session)

            except Exception:
                self.logger.exception("Unexpected error while processing outbox.")

            finally:
                session.close()

            await asyncio.sleep(self.poll_interval.total_seconds())

    async def process_batch(self, session: Session) -> None:
        events = self._claim_batch(session)

        if not events:
            return

        for event in events:
            try:
                await self._publish_event(event)

                self._mark_published(event)

                session.commit()

            except Exception:
                session.rollback()

                self._mark_failed(event)

                try:
                    session.commit()

                except Exception:
                    session.rollback()
                    self.logger.exception("Failed to update retry information.")

    def _claim_batch(
        self,
        session: Session,
    ) -> list[OutboxEvent]:

        now = datetime.now(timezone.utc)

        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .where(OutboxEvent.retry_count < self.max_retry_count)
            .where(
                or_(
                    OutboxEvent.worker_id.is_(None),
                    OutboxEvent.lease_expires_at < now,
                )
            )
            .order_by(OutboxEvent.created_at)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
        )

        events = list(session.scalars(stmt))

        lease_expiry = now + self.lease_duration

        for event in events:
            event.worker_id = self.worker_id
            event.lease_expires_at = lease_expiry

        session.commit()

        return events

    async def _publish_event(
        self,
        event: OutboxEvent,
    ) -> None:

        await self.broker.publish(
            event_type=event.event_type,
            payload=event.payload,
        )

    def _mark_published(
        self,
        event: OutboxEvent,
    ) -> None:

        event.published_at = datetime.now(timezone.utc)
        event.worker_id = None
        event.lease_expires_at = None

    def _mark_failed(
        self,
        event: OutboxEvent,
    ) -> None:

        event.retry_count += 1
        event.worker_id = None
        event.lease_expires_at = None

        if event.retry_count >= self.max_retry_count:
            self.logger.error(
                "Event %s exceeded retry limit.",
                event.id,
            )
