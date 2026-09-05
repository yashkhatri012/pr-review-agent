"""FastAPI application entrypoint for the PR Review Agent backend"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from api.review import router as review_router
from config.settings import get_settings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

load_dotenv()

def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered Pull Request review backend (API only, no frontend).",
        version="0.1.0",
    )
    app.include_router(review_router)
    app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )
    return app


app = create_app()
