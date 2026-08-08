from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_auth_service
from app.schemas.auth import RegisterRequest, UserResponse
from app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:

    user = auth_service.register(
        name=request.name,
        email=request.email,
        password=request.password,
    )

    return UserResponse.model_validate(user)
