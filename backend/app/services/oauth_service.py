from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from pymongo.database import Database

from app.core.config import settings
from app.schemas.auth import TokenResponse
from app.services import auth_service, software_service, user_service
from app.services.user_service import InactiveOAuthUserError

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class OAuthConfigurationError(Exception):
    pass


class OAuthExchangeError(Exception):
    pass


def _require_google_config() -> None:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise OAuthConfigurationError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
        )


def _encode_state(payload: dict) -> str:
    from jose import jwt

    return jwt.encode(
        {
            **payload,
            "type": "oauth_state",
            "nonce": secrets.token_urlsafe(16),
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _decode_state(state: str) -> dict:
    from jose import jwt

    try:
        payload = jwt.decode(
            state,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except Exception as exc:
        raise OAuthExchangeError("Invalid OAuth state.") from exc

    if payload.get("type") != "oauth_state":
        raise OAuthExchangeError("Invalid OAuth state.")
    return payload


AUTH_PAGE_NAMES = frozenset(
    {
        "login",
        "signup",
        "sign up",
        "sign-up",
        "register",
        "initial page",
        "initial",
    }
)


def _resolve_post_login_page_id(
    db: Database, *, software_id: str, login_page_id: str | None = None
) -> str | None:
    pages = list(db.pages.find({"software_id": software_id}).sort("created_at", 1))
    if not pages:
        return None

    exclude_id = (login_page_id or "").strip()

    for page in pages:
        if str(page.get("name", "")).strip().lower() == "home":
            page_id = str(page["_id"])
            if page_id != exclude_id:
                return page_id

    for page in pages:
        page_id = str(page["_id"])
        if exclude_id and page_id == exclude_id:
            continue
        name = str(page.get("name", "")).strip().lower()
        if name in AUTH_PAGE_NAMES:
            continue
        return page_id

    for page in pages:
        page_id = str(page["_id"])
        if exclude_id and page_id == exclude_id:
            continue
        if not page.get("is_default"):
            return page_id

    for page in pages:
        page_id = str(page["_id"])
        if exclude_id and page_id == exclude_id:
            continue
        return page_id

    return None


def build_google_start_url(
    *,
    software_id: str,
    page_id: str,
    return_url: str,
    target_page_id: str | None = None,
) -> str:
    _require_google_config()

    state = _encode_state(
        {
            "provider": "google",
            "software_id": software_id,
            "page_id": page_id,
            "return_url": return_url,
            "target_page_id": target_page_id or "",
        }
    )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def complete_google_callback(db: Database, *, code: str, state: str) -> str:
    _require_google_config()
    state_payload = _decode_state(state)

    token_payload = _exchange_google_code(code)
    profile = _fetch_google_profile(token_payload["access_token"])

    google_sub = profile.get("sub")
    email = profile.get("email")
    name = profile.get("name") or (email.split("@")[0] if email else "Google User")

    if not google_sub or not email:
        raise OAuthExchangeError("Google did not return a usable email address.")

    software_id = state_payload.get("software_id", "")
    software = software_service.get_software(db, software_id)
    if software is None:
        raise OAuthExchangeError("App not found for this login.")

    user = user_service.find_or_create_google_user(
        db,
        organization_id=software.organization_id,
        email=email,
        name=name,
        google_sub=google_sub,
    )

    tokens: TokenResponse = auth_service.issue_tokens_for_user(db, user)

    return_url = state_payload.get("return_url") or f"{settings.FRONTEND_URL}/oauth/callback"
    login_page_id = (state_payload.get("page_id") or "").strip() or None
    target_page_id = (state_payload.get("target_page_id") or "").strip()
    if not target_page_id:
        resolved = _resolve_post_login_page_id(
            db, software_id=software_id, login_page_id=login_page_id
        )
        if resolved:
            target_page_id = resolved

    redirect_params = {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "software_id": software_id,
    }
    if login_page_id:
        redirect_params["page_id"] = login_page_id
    if target_page_id:
        redirect_params["target_page_id"] = target_page_id

    separator = "&" if "?" in return_url else "?"
    return f"{return_url}{separator}{urlencode(redirect_params)}"


def _exchange_google_code(code: str) -> dict:
    try:
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise OAuthExchangeError("Failed to exchange Google authorization code.") from exc


def _fetch_google_profile(access_token: str) -> dict:
    try:
        response = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise OAuthExchangeError("Failed to load Google profile.") from exc


def oauth_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, OAuthConfigurationError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, OAuthExchangeError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OAuth failed.")
