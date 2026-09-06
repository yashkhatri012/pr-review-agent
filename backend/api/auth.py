"""Authentication API routes."""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeSerializer
from pymongo.database import Database

from auth.database import get_database
from auth.dependencies import get_current_user
from auth.google import (
    build_google_authorization_url,
    exchange_code_for_user,
    generate_code_challenge,
    generate_code_verifier,
)
from config.settings import Settings, get_settings


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


OAUTH_STATE_SALT = "pr-review-agent-oauth-state"


def _get_state_serializer(
    settings: Settings,
) -> URLSafeSerializer:
    """Create the OAuth state serializer."""

    return URLSafeSerializer(
        settings.session_secret,
        salt=OAUTH_STATE_SALT,
    )


def _get_session_serializer(
    settings: Settings,
) -> URLSafeSerializer:
    """Create the session serializer."""

    return URLSafeSerializer(
        settings.session_secret,
        salt="pr-review-agent-session",
    )


@router.get("/google")
async def google_login(
    settings: Settings = Depends(get_settings),
):
    """Start Google OAuth."""

    state = secrets.token_urlsafe(32)
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    serializer = _get_state_serializer(settings)

    state_payload = serializer.dumps(
        {
            "state": state,
            "code_verifier": code_verifier,
        }
    )

    authorization_url = build_google_authorization_url(
        settings,
        state=state,
        code_challenge=code_challenge,
    )

    response = RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_302_FOUND,
    )

    response.set_cookie(
        key="oauth_state",
        value=state_payload,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=600,
        path="/",
    )

    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_database),
):
    """Handle the Google OAuth callback."""

    code = request.query_params.get("code")
    returned_state = request.query_params.get("state")
    oauth_state = request.cookies.get("oauth_state")

    if not code or not returned_state or not oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth callback.",
        )

    serializer = _get_state_serializer(settings)

    try:
        state_payload = serializer.loads(
            oauth_state,
            max_age=600,
        )
    except BadSignature as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state.",
        ) from exc

    expected_state = state_payload.get("state")
    code_verifier = state_payload.get("code_verifier")

    if (
        not expected_state
        or not code_verifier
        or not secrets.compare_digest(
            returned_state,
            expected_state,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state.",
        )

    try:
        google_user = await exchange_code_for_user(
            settings,
            code=code,
            code_verifier=code_verifier,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed.",
        ) from exc

    google_id = google_user.get("sub")

    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google did not provide a user ID.",
        )

    existing_user = db.users.find_one(
        {"google_id": google_id},
    )

    if existing_user is None:
        db.users.insert_one(
            {
                "google_id": google_id,
                "email": google_user.get("email"),
                "name": google_user.get("name"),
                "picture": google_user.get("picture"),
                "created_at": __import__(
                    "datetime"
                ).datetime.now(
                    __import__("datetime").timezone.utc
                ),
                "free_review_used": False,
            }
        )
    else:
        db.users.update_one(
            {"google_id": google_id},
            {
                "$set": {
                    "email": google_user.get("email"),
                    "name": google_user.get("name"),
                    "picture": google_user.get("picture"),
                }
            },
        )

    session_serializer = _get_session_serializer(settings)

    session_token = session_serializer.dumps(
        {
            "google_id": google_id,
        }
    )

    response = RedirectResponse(
        url=settings.frontend_url,
        status_code=status.HTTP_302_FOUND,
    )

    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=int(
            timedelta(days=7).total_seconds()
        ),
        path="/",
    )

    response.delete_cookie(
        key="oauth_state",
        path="/",
    )

    return response


@router.get("/me")
async def get_me(
    current_user: dict[str, Any] = Depends(
        get_current_user
    ),
) -> dict[str, Any]:
    """Return the authenticated user's public information."""

    return {
        "id": str(current_user["_id"]),
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "picture": current_user.get("picture"),
        "free_review_used": current_user.get(
            "free_review_used",
            False,
        ),
    }


@router.post("/logout")
async def logout() -> JSONResponse:
    """Log out the current user."""

    response = JSONResponse(
        {
            "status": "logged_out",
        }
    )

    response.delete_cookie(
        key="session",
        path="/",
    )

    return response