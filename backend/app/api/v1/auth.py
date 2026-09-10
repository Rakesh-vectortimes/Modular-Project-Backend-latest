from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pymongo.database import Database

from app.api.deps import get_current_user
from app.db.mongo import get_db
from app.schemas.auth import (
    AppSignupRequest,
    AppSignupResponse,
    LoginRequest,
    LogoutRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.schemas.user import CurrentUser, MeResponse
from app.services import auth_service, oauth_service
from app.services.user_service import InactiveOAuthUserError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Database = Depends(get_db)):
    try:
        return auth_service.register(db, data)
    except auth_service.EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Database = Depends(get_db)):
    try:
        return auth_service.login(db, data)
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except auth_service.InactiveUserError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/app-signup", response_model=AppSignupResponse, status_code=status.HTTP_201_CREATED)
def app_signup(data: AppSignupRequest, db: Database = Depends(get_db)):
    """Public signup from a builder page (maps field keys → user account + profile)."""
    try:
        return auth_service.app_signup(db, data)
    except auth_service.EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except auth_service.SignupValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/me", response_model=MeResponse)
def me(
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return auth_service.get_me(db, current_user.id)
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: LogoutRequest, db: Database = Depends(get_db)):
    auth_service.logout(db, data.refresh_token)
    return None


@router.get("/oauth/google/start")
def google_oauth_start(
    software_id: str,
    page_id: str,
    return_url: str = "",
    target_page_id: str | None = None,
):
    """Redirect the browser to Google sign-in for an app end-user."""
    try:
        url = oauth_service.build_google_start_url(
            software_id=software_id,
            page_id=page_id,
            return_url=return_url,
            target_page_id=target_page_id,
        )
    except oauth_service.OAuthConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/oauth/google/callback")
def google_oauth_callback(
    code: str,
    state: str,
    db: Database = Depends(get_db),
):
    """Google redirects here after the user approves access."""
    try:
        redirect_url = oauth_service.complete_google_callback(db, code=code, state=state)
    except InactiveOAuthUserError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (oauth_service.OAuthConfigurationError, oauth_service.OAuthExchangeError) as exc:
        raise oauth_service.oauth_http_exception(exc) from exc
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
