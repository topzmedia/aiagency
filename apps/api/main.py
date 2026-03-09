from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.database import engine
from apps.api.routers import searches, results, collections, ingestion

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    logger.info("Content Finder API starting up (env=%s)", settings.APP_ENV)
    yield
    logger.info("Content Finder API shutting down")
    await engine.dispose()


app = FastAPI(
    title="Content Finder API",
    version="1.0.0",
    description="Keyword-driven multimodal video content finder",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(searches.router)
app.include_router(results.router)
app.include_router(collections.router)
app.include_router(ingestion.router)


@app.get("/api/health", tags=["health"])
@app.get("/health", tags=["health"], include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "env": settings.APP_ENV}
