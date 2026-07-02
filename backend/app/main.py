from fastapi import FastAPI

app = FastAPI(
    title="Production AI Platform",
    version="0.1.0",
    description="Production-grade AI Platform built with FastAPI.",
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Production AI Platform 🚀"
    }