"""MongoDB connection and database helpers."""

from __future__ import annotations

from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from config.settings import get_settings


@lru_cache
def get_mongo_client() -> MongoClient:
    """Return the shared MongoDB client."""

    settings = get_settings()

    if not settings.mongodb_uri:
        raise ValueError("MONGODB_URI is not configured.")

    return MongoClient(settings.mongodb_uri)


def get_database() -> Database:
    """Return the application database."""

    settings = get_settings()

    return get_mongo_client()[settings.mongodb_database]


def initialize_database() -> None:
    """Create required MongoDB indexes."""

    db = get_database()

    db.users.create_index(
        "google_id",
        unique=True,
    )