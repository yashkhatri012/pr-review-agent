"""Google OAuth helpers."""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Any

import httpx

from config.settings import Settings


GOOGLE_AUTHORIZATION_URL = (
    "https://accounts.google.com/o/oauth2/v2/auth"
)

GOOGLE_TOKEN_URL = (
    "https://oauth2.googleapis.com/token"
)

GOOGLE_USERINFO_URL = (
    "https://openidconnect.googleapis.com/v1/userinfo"
)


def generate_code_verifier() -> str:
    """Generate a PKCE code verifier."""

    return secrets.token_urlsafe(64)


def generate_code_challenge(code_verifier: str) -> str:
    """Generate a PKCE S256 code challenge."""

    digest = hashlib.sha256(
        code_verifier.encode("ascii")
    ).digest()

    return base64.urlsafe_b64encode(
        digest
    ).rstrip(b"=").decode("ascii")


def build_google_authorization_url(
    settings: Settings,
    *,
    state: str,
    code_challenge: str,
) -> str:
    """Build the Google OAuth authorization URL."""

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }

    return str(
        httpx.URL(
            GOOGLE_AUTHORIZATION_URL,
            params=params,
        )
    )


async def exchange_code_for_user(
    settings: Settings,
    *,
    code: str,
    code_verifier: str,
) -> dict[str, Any]:
    """Exchange the authorization code and retrieve Google user info."""

    token_payload = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.google_redirect_uri,
        "code_verifier": code_verifier,
    }

    async with httpx.AsyncClient(
        timeout=10.0,
    ) as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data=token_payload,
        )

        token_response.raise_for_status()

        token_data = token_response.json()

        access_token = token_data.get("access_token")

        if not access_token:
            raise ValueError(
                "Google did not return an access token."
            )

        user_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        user_response.raise_for_status()

        return user_response.json()