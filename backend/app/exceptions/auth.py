from app.exceptions.base import DomainError


class AuthError(DomainError):
    pass


class UserAlreadyExistsError(AuthError):
    def __init__(self):
        super().__init__("A user with this email already exists.")


class InvalidTokenError(AuthError):
    def __init__(self):
        super().__init__("Invalid authentication token.")


class InvalidCredentialsError(AuthError):
    def __init__(self):
        super().__init__("Invalid email or password.")