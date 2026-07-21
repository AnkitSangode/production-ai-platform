class OutboxPublisher:
    def __init__(
        self,
        session_factory,
        message_broker,
        logger,
    ):
        def run(self):
            while True:
                try:
                    with self.session_factory() as session:
                        processed = self.process_batch(session)

                    if not processed:
                        sleep(...)
                except RecoverableError as e:
                    logger.warning(...)
                    sleep(...)