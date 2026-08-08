from app.core.security import hash_password
from app.db.models.user import User
from app.exceptions.auth import UserAlreadyExistsError
from app.dependencies.uow import UnitOfWork


class AuthService:

    def __init__(
        self,
        uow: UnitOfWork,
    ):
        self.uow = uow

    def register(
        self,
        name: str,
        email: str,
        password: str,
    ) -> User:

        email = email.strip().lower()

        try:
            existing_user = (
                self.uow.user_repository.get_by_email(email)
            )

            if existing_user is not None:
                raise UserAlreadyExistsError()

            hashed_password = hash_password(password)

            user = User(
                name=name,
                email=email,
                hashed_password=hashed_password,
            )

            self.uow.user_repository.create(user)

            self.uow.commit()

            return user

        except Exception:
            self.uow.rollback()
            raise