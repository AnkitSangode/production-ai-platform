from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.exceptions.auth import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)

from app.db.models.user import User
from app.dependencies.uow import UnitOfWork
from app.core.config import Settings



class AuthService:

    def __init__(
        self,
        uow: UnitOfWork,
        settings: Settings,
    ):
        self.uow = uow
        self.settings = settings

    def register(
        self,
        name: str,
        email: str,
        password: str,
    ) -> User:

        email = email.strip().lower()

        try:
            existing_user = self.uow.user.get_by_email(email)

            if existing_user is not None:
                raise UserAlreadyExistsError()

            hashed_password = hash_password(password)

            user = User(
                name=name,
                email=email,
                hashed_password=hashed_password,
            )

            self.uow.user.create(user)

            self.uow.commit()

            return user

        except Exception:
            self.uow.rollback()
            raise

    def login(
        self,
        email: str,
        password: str,
    ) -> str:

        email = email.strip().lower()

        user = self.uow.user.get_by_email(email)

        if user is None:
            raise InvalidCredentialsError()

        if not verify_password(
            password,
            user.hashed_password,
        ):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError()

        return create_access_token(
            user.id,
            self.settings,
        )
