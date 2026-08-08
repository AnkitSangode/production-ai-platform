from fastapi import Depends

from app.dependencies.uow import UnitOfWork,get_unit_of_work
from app.services.auth import AuthService


def get_auth_service(
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> AuthService:
    return AuthService(uow=uow)