"""Authentication dependencies."""

from __future__ import annotations

from typing import Any

from fastapi import Cookie, Depends, HTTPException, status
from itsdangerous import BadSignature, URLSafeSerializer
from pymongo.database import Database

from auth.database import get_database
from config.settings import Settings, get_settings


SESSION_SALT = "pr-review-agent-session"


def _get_serializer(
    settings: Settings,
) -> URLSafeSerializer:
    """Create the session serializer."""

    return URLSafeSerializer(
        settings.session_secret,
        salt=SESSION_SALT,
    )


def get_current_user(
    session: str | None = Cookie(default=None),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_database),
) -> dict[str, Any]:
    """Return the authenticated user."""

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    serializer = _get_serializer(settings)

    try:
        payload = serializer.loads(session)
    except BadSignature as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        ) from exc

    google_id = payload.get("google_id")

    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        )

    user = db.users.find_one(
        {"google_id": google_id},
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )

    return user