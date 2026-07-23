class OutboxPublisher:
    def __init__(
        self,
        session_factory: sessionmaker,
        broker: MessageBroker,
        worker_id: str,
        batch_size: int = 100,
        lease_duration: timedelta = timedelta(minutes=5),
        poll_interval: timedelta = timedelta(seconds=5),
        logger,
    ) -> None:

        self.session_factory = session_factory
        self.broker = broker
        self.worker_id = worker_id
        self.batch_size = batch_size
        self.lease_duration = lease_duration
        self.poll_interval = poll_interval
        self.logger = logger

    def run(self) -> None:
        while True:
            try:
                with self.session_factory() as session:
                    work_done = self.process_batch(session)

                if not work_done:
                    time.sleep(self.poll_interval.total_seconds())
            except RecoverableError as e:
                logger.warning(...)
                sleep(...)

    def process_batch(self, session): ...

    def _claim_batch(self, session: Session) -> list[OutboxEvent]:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .where(
                or_(
                    OutboxEvent.worker_id.is_(None),
                    OutboxEvent.lease_expires_at < func.now(),
                )
            )
            .order_by(OutboxEvent.created_at)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
        )

        events = session.scalars(stmt).all()

        lease_expiry = datetime.now(timezone.utc) + timedelta(
            minutes=self.lease_duration
        )

        for event in events:
            event.worker_id = self.worker_id
            event.lease_expires_at = lease_expiry

        return events

    def _publish_event(self, event): ...

    def _mark_published(self, session, event): ...
