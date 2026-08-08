from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.document import router as document_router


app = FastAPI(
    title="Production AI Platform",
    version="0.1.0",
    description="Production-grade AI Platform built with FastAPI.",
)


app.include_router(auth_router)
app.include_router(document_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Production AI Platform 🚀"
    }