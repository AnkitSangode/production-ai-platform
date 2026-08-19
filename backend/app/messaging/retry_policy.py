class RetryPolicy:

    def __init__(
        self,
        max_attempts: int,
    ) -> None:
        if max_attempts < 1:
            raise ValueError(
                "max_attempts must be greater than or equal to 1."
            )

        self.max_attempts = max_attempts

    def should_retry(
        self,
        acquired_count: int,
    ) -> bool:

        if acquired_count < 0:
            raise ValueError(
                "acquired_count must be greater than or equal to 0."
            )

        attempt_number = acquired_count + 1

        return attempt_number < self.max_attempts

        