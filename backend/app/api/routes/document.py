from fastapi import APIRouter, Depends, File, UploadFile, status

from app.dependencies. import get_current_user
from app.dependencies.service import get_document_service
from app.db.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    return document_service.upload(
        file=file,
        user_id=current_user.id,
    )