import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.logging import get_logger
from app.messaging.base import (
    BrokerConnectionError,
    MessageBroker,
    MessagePublishError,
)
from app.messaging.contracts import ClaimedOutboxMessage
from app.uow.unit_of_work import UnitOfWork

UoWFactory = Callable[[], UnitOfWork]

logger = get_logger(__name__)


class OutboxPublisher:
    """
    Publishes PostgreSQL outbox events to a message broker.

    Responsibilities:
    - claim events from the outbox
    - establish durable ownership
    - publish events to the broker
    - mark successfully published events
    - continuously poll for new events
    - handle graceful shutdown

    Does NOT:
    - perform SQL directly
    - know RabbitMQ internals
    - manage RabbitMQ connection/reconnection internals
    - serialize broker messages
    """

    def __init__(
        self,
        broker: MessageBroker,
        uow_factory: UoWFactory,
        *,
        batch_size: int = 100,
        poll_interval: float = 5.0,
        lease_seconds: int = 60,
        max_retry_count: int = 5,
    ) -> None:
        self.broker = broker
        self.uow_factory = uow_factory

        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.lease_seconds = lease_seconds
        self.max_retry_count = max_retry_count

        # Unique identity for this publisher process.
        self.worker_id = f"outbox-publisher-{uuid4()}"

        self._shutdown_event = asyncio.Event()

    # =========================================================
    # CLAIM
    # =========================================================

    def claim_batch(
        self,
    ) -> list[ClaimedOutboxMessage]:
        """
        Claim a batch of unpublished outbox events.

        The repository:
        - selects eligible events
        - locks them
        - assigns this worker as owner
        - assigns a lease

        We then commit that ownership before
        attempting to publish to the broker.
        """

        now = datetime.now(timezone.utc)

        lease_expires_at = now + timedelta(seconds=self.lease_seconds)

        with self.uow_factory() as uow:

            messages = uow.outbox.claim_batch(
                worker_id=self.worker_id,
                now=now,
                lease_expires_at=lease_expires_at,
                batch_size=self.batch_size,
                max_retry_count=self.max_retry_count,
            )

            # Ownership becomes durable here.
            uow.commit()

            return messages

    # =========================================================
    # MARK PUBLISHED
    # =========================================================

    def mark_published(
        self,
        message: ClaimedOutboxMessage,
    ) -> bool:
        """
        Mark an event as published only if this worker
        still owns the event.

        Returns:
            True  -> event successfully marked published
            False -> ownership was lost
        """

        with self.uow_factory() as uow:

            updated = uow.outbox.mark_published(
                event_id=message.event_id,
                worker_id=message.worker_id,
                published_at=datetime.now(timezone.utc),
            )

            if not updated:
                logger.warning(
                    "Lost ownership of outbox event before " "marking it published",
                    extra={
                        "event_id": str(message.event_id),
                        "worker_id": message.worker_id,
                    },
                )

                uow.rollback()

                return False

            uow.commit()

            return True

    # =========================================================
    # MARK FAILED
    # =========================================================

    def mark_failed(
        self,
        message: ClaimedOutboxMessage,
    ) -> bool:
        """
        Mark an event as failed.

        This method is intentionally not used automatically
        by publish_one() yet.

        Retry policy will be introduced separately.
        """

        with self.uow_factory() as uow:

            updated = uow.outbox.mark_failed(
                event_id=message.event_id,
                worker_id=message.worker_id,
            )

            if not updated:
                logger.warning(
                    "Lost ownership while marking " "outbox event failed",
                    extra={
                        "event_id": str(message.event_id),
                        "worker_id": message.worker_id,
                    },
                )

                uow.rollback()

                return False

            uow.commit()

            return True

    # =========================================================
    # PUBLISH ONE
    # =========================================================

    async def publish_one(
        self,
        message: ClaimedOutboxMessage,
    ) -> None:
        """
        Publish one claimed outbox event.

        Lifecycle:

            publish to broker
                ↓
            broker confirmation
                ↓
            mark published in PostgreSQL

        We NEVER mark the event as published before
        the broker confirms publication.
        """

        # -----------------------------------------------------
        # 1. Publish to broker
        # -----------------------------------------------------

        try:

            await self.broker.publish(
                message_id=message.event_id,
                event_type=message.event_type,
                payload=message.payload,
            )

        except BrokerConnectionError:
            logger.exception(
                "Broker connection failed while publishing " "outbox event",
                extra={
                    "event_id": str(message.event_id),
                    "worker_id": message.worker_id,
                    "event_type": message.event_type.value,
                },
            )

            raise

        except MessagePublishError:
            logger.exception(
                "Broker rejected outbox event publication",
                extra={
                    "event_id": str(message.event_id),
                    "worker_id": message.worker_id,
                    "event_type": message.event_type.value,
                },
            )

            raise

        # -----------------------------------------------------
        # 2. Broker confirmed publication
        # -----------------------------------------------------

        marked = self.mark_published(message)

        if not marked:
            raise RuntimeError(
                f"Lost ownership of outbox event "
                f"{message.event_id} before marking it published."
            )

    # =========================================================
    # RUN ONCE
    # =========================================================

    async def run_once(self) -> None:
        """
        Execute one publishing cycle.

        Flow:

            broker ready
                ↓
            claim batch
                ↓
            commit ownership
                ↓
            publish each message
                ↓
            mark successful messages published
        """

        # -----------------------------------------------------
        # 1. Make sure broker is available
        # -----------------------------------------------------

        if not self.broker.is_ready:

            await self.broker.wait_until_ready()

            if not self.broker.is_ready:
                return

        # -----------------------------------------------------
        # 2. Claim events
        # -----------------------------------------------------

        messages = self.claim_batch()

        if not messages:
            return

        # -----------------------------------------------------
        # 3. Publish claimed events
        # -----------------------------------------------------

        for message in messages:

            if self._shutdown_event.is_set():
                return

            try:

                await self.publish_one(message)

            except BrokerConnectionError:
                """
                RabbitMQ connection is unavailable.

                Stop this batch immediately.

                We do not want to keep trying to publish
                other messages when the broker itself is down.
                """

                raise

            except MessagePublishError:
                """
                The broker rejected this particular publication.

                Leave the event unpublished.

                Its lease remains active and it can be
                reclaimed after the lease expires.
                """

                continue

            except Exception:
                """
                Unexpected error.

                This could include a PostgreSQL failure after
                RabbitMQ already confirmed the message.

                Therefore we DO NOT mark the event failed here.
                """

                logger.exception(
                    "Unexpected error while processing " "outbox event",
                    extra={
                        "event_id": str(message.event_id),
                        "worker_id": message.worker_id,
                        "event_type": message.event_type.value,
                    },
                )

                continue

    # =========================================================
    # STOP
    # =========================================================

    def stop(self) -> None:
        """
        Request graceful shutdown.
        """

        logger.info(
            "Outbox publisher shutdown requested",
            extra={
                "worker_id": self.worker_id,
            },
        )

        self._shutdown_event.set()

    # =========================================================
    # RUN FOREVER
    # =========================================================

    async def run_forever(self) -> None:
        """
        Run the outbox publisher continuously.

        Startup:

            connect
                ↓

        Runtime:

            run_once
                ↓
            wait
                ↓
            run_once
                ↓
            ...

        Shutdown:

            stop
                ↓
            close broker
        """

        logger.info(
            "Starting outbox publisher",
            extra={
                "worker_id": self.worker_id,
            },
        )

        # -----------------------------------------------------
        # INITIAL CONNECTION
        # -----------------------------------------------------

        try:

            await self.broker.connect()

        except BrokerConnectionError:

            logger.exception(
                "Initial broker connection failed",
                extra={
                    "worker_id": self.worker_id,
                },
            )

            raise

        # -----------------------------------------------------
        # MAIN LOOP
        # -----------------------------------------------------

        try:

            while not self._shutdown_event.is_set():

                try:

                    await self.run_once()

                except BrokerConnectionError:

                    logger.warning(
                        "Broker connection lost. " "Waiting for broker recovery.",
                        extra={
                            "worker_id": self.worker_id,
                        },
                    )

                    try:
                        await self.broker.wait_until_ready()

                    except BrokerConnectionError:

                        logger.exception(
                            "Broker recovery failed",
                            extra={
                                "worker_id": self.worker_id,
                            },
                        )

                        break

                except Exception:

                    logger.exception(
                        "Unexpected error in outbox publisher cycle",
                        extra={
                            "worker_id": self.worker_id,
                        },
                    )

                # -------------------------------------------------
                # POLL INTERVAL
                # -------------------------------------------------

                try:

                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.poll_interval,
                    )

                except asyncio.TimeoutError:
                    pass

        finally:

            logger.info(
                "Closing outbox publisher",
                extra={
                    "worker_id": self.worker_id,
                },
            )

            await self.broker.close()
