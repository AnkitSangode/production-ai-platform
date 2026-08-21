class RetryableError(Exception):
    """The operation failed temporarily and may succeed if retried."""


class PermanentError(Exception):
    """The operation cannot succeed by retrying."""

class RetryExhaustedError(Exception):
    pass