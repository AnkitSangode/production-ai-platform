from app.exceptions.base import DomainError


class AuthError(DomainError):
    """Base exception for authentication-related errors."""

    pass


class UserAlreadyExistsError(AuthError):
    pass
