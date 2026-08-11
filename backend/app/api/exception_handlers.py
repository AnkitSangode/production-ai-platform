from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.error_codes import ErrorCode
from app.exceptions.auth import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.exceptions.base import DomainError
from app.exceptions.document import (
    DocumentNotFoundError,
    DocumentTooLargeError,
    EmptyFileError,
    UnsupportedFileTypeError,
)


DOMAIN_ERROR_MAP = {
    UserAlreadyExistsError: (
        HTTPStatus.CONFLICT,
        ErrorCode.USER_ALREADY_EXISTS,
    ),
    InvalidCredentialsError: (
        HTTPStatus.UNAUTHORIZED,
        ErrorCode.INVALID_CREDENTIALS,
    ),
    InvalidTokenError: (
        HTTPStatus.UNAUTHORIZED,
        ErrorCode.INVALID_TOKEN,
    ),
    DocumentNotFoundError: (
        HTTPStatus.NOT_FOUND,
        ErrorCode.DOCUMENT_NOT_FOUND,
    ),
    DocumentTooLargeError: (
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        ErrorCode.DOCUMENT_TOO_LARGE,
    ),
    UnsupportedFileTypeError: (
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        ErrorCode.UNSUPPORTED_FILE_TYPE,
    ),
    EmptyFileError: (
        HTTPStatus.BAD_REQUEST,
        ErrorCode.EMPTY_FILE,
    ),
}


async def domain_error_handler(
    request: Request,
    exc: DomainError,
) -> JSONResponse:

    status_code, error_code = DOMAIN_ERROR_MAP[type(exc)]

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code.value,
                "message": str(exc),
            }
        },
    )