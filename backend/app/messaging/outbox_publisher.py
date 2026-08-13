import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from app.messaging.base import (
    BrokerConnectionError,
    MessageBroker,
    MessagePublishError,
)
from app.uow.unit_of_work import UnitOfWork
from collections.abc import Callable

UoWFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True)
class ClaimedOutboxMessage:
    """
    Immutable representation of a claimed outbox event.

    We intentionally don't pass SQLAlchemy ORM objects
    into RabbitMQ-related code.
    """

    event_id: UUID
    event_type: str
    payload: dict[str, Any]
    worker_id: str


class OutboxPublisher:
    """
    Publishes PostgreSQL outbox events to a message broker.

    Responsibilities:
    - claim events
    - establish durable ownership
    - publish events
    - mark successful events as published
    - mark definite failures
    - handle broker outages
    - poll continuously
    - graceful shutdown

    Does NOT:
    - perform SQL directly
    - know RabbitMQ internals
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
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 30.0,
    ) -> None:

        self.broker = broker
        self.uow_factory = uow_factory

        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.lease_seconds = lease_seconds
        self.max_retry_count = max_retry_count

        self.reconnect_base_delay = reconnect_base_delay
        self.reconnect_max_delay = reconnect_max_delay

        # Unique identity for this publisher process.
        self.worker_id = f"outbox-publisher-{uuid4()}"

        self._shutdown_event = asyncio.Event()

    # =========================================================
    # CONNECTION
    # =========================================================

    async def _connect_with_retry(self) -> None:
        """
        Establish the initial broker connection.

        Uses exponential backoff.

        1s
        2s
        4s
        8s
        ...
        max 30s
        """

        attempt = 0

        while not self._shutdown_event.is_set():

            try:
                await self.broker.connect()

                print(f"[{self.worker_id}] " "Connected to message broker.")

                return

            except BrokerConnectionError as exc:

                delay = min(
                    self.reconnect_base_delay * (2**attempt),
                    self.reconnect_max_delay,
                )

                attempt += 1

                print(
                    f"[{self.worker_id}] "
                    f"Broker connection failed. "
                    f"Retrying in {delay:.1f}s. "
                    f"Attempt={attempt}. "
                    f"Error={exc}"
                )

                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=delay,
                    )

                except asyncio.TimeoutError:
                    pass

    async def _wait_for_broker_recovery(self) -> bool:
        """
        Wait for an established robust broker connection
        to recover.

        Returns:
            True  -> broker recovered
            False -> shutdown requested
        """

        if self._shutdown_event.is_set():
            return False

        try:
            await self.broker.wait_until_ready()

            print(f"[{self.worker_id}] " "Message broker recovered.")

            return True

        except BrokerConnectionError as exc:

            print(f"[{self.worker_id}] " f"Broker recovery failed: {exc}")

            return False

    # =========================================================
    # CLAIM
    # =========================================================

    def claim_batch(
        self,
    ) -> list[ClaimedOutboxMessage]:

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
        Mark an event published only if this publisher
        still owns it.
        """

        with self.uow_factory() as uow:

            updated = uow.outbox.mark_published(
                event_id=message.event_id,
                worker_id=self.worker_id,
                published_at=datetime.now(timezone.utc),
            )

            if not updated:

                uow.rollback()

                print(
                    f"[{self.worker_id}] "
                    f"Lost ownership of event "
                    f"{message.event_id}."
                )

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
        Mark a definitively failed publication attempt.

        Only succeeds if this publisher still owns the event.
        """

        with self.uow_factory() as uow:

            updated = uow.outbox.mark_failed(
                event_id=message.event_id,
                worker_id=self.worker_id,
            )

            if not updated:

                uow.rollback()

                print(
                    f"[{self.worker_id}] "
                    f"Lost ownership while marking "
                    f"{message.event_id} failed."
                )

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
        Publish one claimed event.

        Success:
            publish
              ↓
            mark_published

        Definite failure:
            publish
              ↓
            mark_failed

        Connection failure:
            publish
              ↓
            KEEP LEASE
              ↓
            propagate error
        """

        try:

            await self.broker.publish(
                message_id=message.event_id,
                event_type=message.event_type,
                payload=message.payload,
            )

        except MessagePublishError as exc:

            print(
                f"[{self.worker_id}] "
                f"Message publication failed for "
                f"{message.event_id}: {exc}"
            )

            self.mark_failed(message)

            return

        except BrokerConnectionError:

            print(
                f"[{self.worker_id}] "
                f"Broker connection lost while publishing "
                f"{message.event_id}."
            )

            # IMPORTANT:
            #
            # We intentionally DO NOT call mark_failed().
            #
            # The message may already have reached RabbitMQ.
            # Therefore the publication outcome is uncertain.
            #
            # Keep the lease and let the broker recover.

            raise

        published = self.mark_published(message)

        if not published:

            print(
                f"[{self.worker_id}] "
                f"Event {message.event_id} was published "
                f"but ownership was lost before the "
                f"database update."
            )

    # =========================================================
    # RUN ONCE
    # =========================================================

    async def run_once(self) -> None:
        """
        Execute one publishing cycle.

        Important:
        We never claim new events while the broker
        is known to be unavailable.
        """

        if not self.broker.is_ready:

            recovered = await self._wait_for_broker_recovery()

            if not recovered:
                return

        messages = self.claim_batch()

        if not messages:
            return

        for message in messages:

            if self._shutdown_event.is_set():
                return

            await self.publish_one(message)

    # =========================================================
    # STOP
    # =========================================================

    def stop(self) -> None:
        """
        Request graceful shutdown.
        """

        print(f"[{self.worker_id}] " "Shutdown requested.")

        self._shutdown_event.set()

    # =========================================================
    # RUN FOREVER
    # =========================================================

    async def run_forever(self) -> None:
        """
        Main publisher lifecycle.

        Startup:

            connect
              ↓
            retry if necessary

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

        print(f"[{self.worker_id}] " "Starting outbox publisher.")

        # -----------------------------------------------------
        # INITIAL CONNECTION
        # -----------------------------------------------------

        await self._connect_with_retry()

        if self._shutdown_event.is_set():
            return

        # -----------------------------------------------------
        # MAIN LOOP
        # -----------------------------------------------------

        try:

            while not self._shutdown_event.is_set():

                try:

                    await self.run_once()

                except BrokerConnectionError:

                    print(
                        f"[{self.worker_id}] "
                        "Broker connection lost. "
                        "Pausing publishing."
                    )

                    recovered = await self._wait_for_broker_recovery()

                    if not recovered:
                        break

                except Exception:

                    print(f"[{self.worker_id}] " "Unexpected error in publisher cycle.")

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

            print(f"[{self.worker_id}] " "Closing outbox publisher.")

            await self.broker.close()
