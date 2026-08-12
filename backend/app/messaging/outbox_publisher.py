import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.messaging.base import MessageBroker
from app.uow.factory import create_unit_of_work


logger = get_logger("outbox_publisher")


@dataclass(frozen=True)
class ClaimedOutboxMessage:
    """
    Immutable representation of an outbox event after
    it has been durably claimed.

    We don't carry the SQLAlchemy ORM object across
    the database/network boundary.
    """

    event_id: UUID
    event_type: str
    payload: dict[str, Any]


class OutboxPublisher:
    """
    Publishes unpublished outbox events to the message broker.

    Responsibilities:
    - claim unpublished events
    - publish claimed events
    - mark successfully published events
    - release failed events
    - continuously poll the outbox
    - gracefully shut down

    This class does NOT:
    - perform SQL queries directly
    - manage SQLAlchemy sessions directly
    - know RabbitMQ implementation details
    """

    def __init__(
        self,
        broker: MessageBroker,
        *,
        batch_size: int = 100,
        poll_interval: float = 5.0,
        lease_seconds: int = 60,
        max_retry_count: int = 5,
    ) -> None:
        self.broker = broker

        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.lease_seconds = lease_seconds
        self.max_retry_count = max_retry_count

        # One identity per publisher process.
        self.worker_id = (
            f"outbox-publisher-{uuid4()}"
        )

        self._shutdown_event = asyncio.Event()

    # ---------------------------------------------------------
    # CLAIM
    # ---------------------------------------------------------

    def claim_batch(self) -> list[ClaimedOutboxMessage]:
        """
        Claim a batch of eligible outbox events.

        Transaction flow:

            BEGIN
              ↓
            claim_batch()
              ↓
            assign worker_id + lease
              ↓
            COMMIT
              ↓
            return claimed messages

        The claim becomes durable after commit.
        """

        now = datetime.now(timezone.utc)

        lease_expires_at = (
            now
            + timedelta(
                seconds=self.lease_seconds
            )
        )

        with create_unit_of_work() as uow:

            events = uow.outbox.claim_batch(
                worker_id=self.worker_id,
                now=now,
                lease_expires_at=lease_expires_at,
                batch_size=self.batch_size,
                max_retry_count=self.max_retry_count,
            )

            messages = [
                ClaimedOutboxMessage(
                    event_id=event.id,
                    event_type=event.event_type.value,
                    payload=event.payload,
                )
                for event in events
            ]

            uow.commit()

            logger.info(
                "Claimed outbox events.",
                extra={
                    "worker_id": self.worker_id,
                    "count": len(messages),
                },
            )

            return messages

    # ---------------------------------------------------------
    # MARK PUBLISHED
    # ---------------------------------------------------------

    def mark_published(
        self,
        message: ClaimedOutboxMessage,
    ) -> bool:
        """
        Mark an event as published.

        The repository verifies that this publisher
        still owns the event.

        Returns:
            True  -> event was successfully marked published.
            False -> publisher no longer owns the event.
        """

        with create_unit_of_work() as uow:

            updated = uow.outbox.mark_published(
                event_id=message.event_id,
                worker_id=self.worker_id,
                published_at=datetime.now(
                    timezone.utc
                ),
            )

            if not updated:
                uow.rollback()

                logger.warning(
                    "Lost ownership before marking "
                    "event as published.",
                    extra={
                        "event_id": str(
                            message.event_id
                        ),
                        "worker_id": self.worker_id,
                    },
                )

                return False

            uow.commit()

            return True

    # ---------------------------------------------------------
    # MARK FAILED
    # ---------------------------------------------------------

    def mark_failed(
        self,
        message: ClaimedOutboxMessage,
    ) -> bool:
        """
        Mark a failed publication attempt.

        The repository verifies that this publisher
        still owns the event.

        Returns:
            True  -> failure state was persisted.
            False -> publisher no longer owns the event.
        """

        with create_unit_of_work() as uow:

            updated = uow.outbox.mark_failed(
                event_id=message.event_id,
                worker_id=self.worker_id,
            )

            if not updated:
                uow.rollback()

                logger.warning(
                    "Lost ownership while trying "
                    "to mark event as failed.",
                    extra={
                        "event_id": str(
                            message.event_id
                        ),
                        "worker_id": self.worker_id,
                    },
                )

                return False

            uow.commit()

            return True

    # ---------------------------------------------------------
    # PUBLISH ONE
    # ---------------------------------------------------------

    async def publish_one(
        self,
        message: ClaimedOutboxMessage,
    ) -> None:
        """
        Publish one claimed event.

        Flow:

            RabbitMQ
              │
              ├── success → mark published
              │
              └── failure → mark failed
        """

        try:
            await self.broker.publish(
                message_id=message.event_id,
                event_type=message.event_type,
                payload=message.payload,
            )

        except Exception:
            logger.exception(
                "Failed to publish outbox event.",
                extra={
                    "event_id": str(
                        message.event_id
                    ),
                    "event_type": message.event_type,
                    "worker_id": self.worker_id,
                },
            )

            self.mark_failed(message)

            return

        updated = self.mark_published(message)

        if not updated:
            logger.warning(
                "Event was successfully published to "
                "the broker, but this publisher no "
                "longer owns the outbox event.",
                extra={
                    "event_id": str(
                        message.event_id
                    ),
                    "worker_id": self.worker_id,
                },
            )

    # ---------------------------------------------------------
    # RUN ONCE
    # ---------------------------------------------------------

    async def run_once(self) -> None:
        """
        Execute one complete publishing cycle.

        Flow:

            claim batch
                 ↓
            publish A
                 ↓
            publish B
                 ↓
            publish C
        """

        messages = self.claim_batch()

        if not messages:
            return

        for message in messages:

            if self._shutdown_event.is_set():
                break

            await self.publish_one(message)

    # ---------------------------------------------------------
    # STOP
    # ---------------------------------------------------------

    def stop(self) -> None:
        """
        Request graceful shutdown.
        """

        logger.info(
            "Outbox publisher shutdown requested.",
            extra={
                "worker_id": self.worker_id,
            },
        )

        self._shutdown_event.set()

    # ---------------------------------------------------------
    # RUN FOREVER
    # ---------------------------------------------------------

    async def run_forever(self) -> None:
        """
        Continuously poll and publish outbox events.

        Lifecycle:

            connect
              ↓
            run_once
              ↓
            wait
              ↓
            run_once
              ↓
            wait
              ↓
             ...
              ↓
           shutdown
              ↓
            close
        """

        logger.info(
            "Starting outbox publisher.",
            extra={
                "worker_id": self.worker_id,
            },
        )

        await self.broker.connect()

        try:

            while not self._shutdown_event.is_set():

                try:
                    await self.run_once()

                except Exception:
                    logger.exception(
                        "Unexpected error during "
                        "outbox publishing cycle.",
                        extra={
                            "worker_id": self.worker_id,
                        },
                    )

                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.poll_interval,
                    )

                except asyncio.TimeoutError:
                    pass

        finally:

            logger.info(
                "Stopping outbox publisher.",
                extra={
                    "worker_id": self.worker_id,
                },
            )

            await self.broker.close()