from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.document import router as document_router

from app.api.exception_handlers import domain_error_handler
from app.exceptions.base import DomainError


app = FastAPI(
    title="Production AI Platform",
    version="0.1.0",
    description="Production-grade AI Platform built with FastAPI.",
)


app.add_exception_handler(
    DomainError,
    domain_error_handler,
)


app.include_router(auth_router)
app.include_router(document_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Production AI Platform 🚀"
    }


# @app.get("/debug/error")
# async def debug_error():
#     from app.exceptions.auth import InvalidCredentialsError

#     raise InvalidCredentialsError()


# @app.get("/debug/error")
# async def debug_error():
#     from app.exceptions.document import DocumentTooLargeError

#     raise DocumentTooLargeError(
#         actual_size=30_000_000,
#         max_size=25_000_000,
#     )