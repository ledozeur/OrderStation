from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="OrderStation API",
        description="Учёт заказов БПЛА: заказчики, BOM, закупка, сроки.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
