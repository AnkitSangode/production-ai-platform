import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.repositories.outbox_repository import OutboxRepository
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
    ) -> None:
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
                session.rollback()
                self.logger.exception("Unexpected error while processing outbox.")

            finally:
                session.close()

            await asyncio.sleep(self.poll_interval.total_seconds())

    async def process_batch(
        self,
        session: Session,
    ) -> None:

        repository = OutboxRepository(session)

        now = datetime.now(timezone.utc)

        lease_expires_at = now + self.lease_duration

        events = repository.claim_batch(
            worker_id=self.worker_id,
            now=now,
            lease_expires_at=lease_expires_at,
            batch_size=self.batch_size,
            max_retry_count=self.max_retry_count,
        )

        if not events:
            return

        #
        # Persist the lease immediately.
        #
        session.commit()

        for event in events:

            try:
                await self._publish_event(event)

                event.mark_published(
                    published_at=datetime.now(timezone.utc),
                )

                session.commit()

            except Exception:

                session.rollback()

                event.mark_failed()

                try:
                    session.commit()

                except Exception:
                    session.rollback()

                    self.logger.exception(
                        "Failed to update retry information for event %s",
                        event.id,
                    )

    async def _publish_event(
        self,
        event: OutboxEvent,
    ) -> None:

        await self.broker.publish(
            event_type=event.event_type.value,
            payload=event.payload,
        )
