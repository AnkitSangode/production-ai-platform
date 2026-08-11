from fastapi import Depends

from app.dependencies.uow import UnitOfWork, get_unit_of_work
from app.services.auth import AuthService
from app.core.config import get_settings

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.security import decode_access_token
from app.db.models.user import User
from app.exceptions.auth import InvalidTokenError
from app.uow.unit_of_work import UnitOfWork
from app.dependencies.uow import get_unit_of_work
from app.core.config import Settings, get_settings

bearer_scheme = HTTPBearer()


def get_auth_service(
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        uow=uow,
        settings=settings,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> User:

    token = credentials.credentials

    payload = decode_access_token(
        token,
        settings,
    )

    subject = payload.get("sub")

    if subject is None:
        raise InvalidTokenError()

    try:
        user_id = UUID(subject)
    except (ValueError, TypeError) as exc:
        raise InvalidTokenError() from exc

    user = uow.user.get_by_id(user_id)

    if user is None:
        raise InvalidTokenError()

    if not user.is_active:
        raise InvalidTokenError()

    return user
