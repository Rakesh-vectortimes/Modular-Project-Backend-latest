from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.core.enums import UserRole, UserStatus
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.db.serialize import doc_to_dict
from app.schemas.auth import (
    AppSignupRequest,
    AppSignupResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.schemas.organization import OrganizationSummary
from app.schemas.user import MeResponse, UserCreate, UserRead
from app.services import organization_service, software_service, user_profile_service, user_service
from app.services.field_mapper import map_signup_values


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class EmailAlreadyExistsError(Exception):
    pass


class SignupValidationError(Exception):
    pass


def register(db: Database, data: RegisterRequest) -> RegisterResponse:
    if user_service.get_user_by_email(db, data.email):
        raise EmailAlreadyExistsError("Email is already registered")

    organization = organization_service.create_organization(db, data.organization_name)
    user = user_service.create_user(
        db,
        organization_id=organization.id,
        data=UserCreate(
            name=data.name,
            email=data.email,
            mobile=data.mobile,
            password=data.password,
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
        ),
        actor_role=None,
    )
    tokens = _issue_tokens(db, user)
    return RegisterResponse(
        user=user,
        organization=OrganizationSummary(id=organization.id, name=organization.name),
        tokens=tokens,
    )


def app_signup(db: Database, data: AppSignupRequest) -> AppSignupResponse:
    """Create a member account for the organization that owns `software_id`.

    Form field keys (email, password, firstName, address, pincode, …) are
    mapped automatically — see `field_mapper.map_signup_values`.
    """
    software = software_service.get_software(db, data.software_id)
    if software is None:
        raise SignupValidationError("App not found.")

    user_fields, profile_fields = map_signup_values(data.values)

    email = user_fields.get("email")
    password = user_fields.get("password")
    name = user_fields.get("name")

    if not email:
        raise SignupValidationError(
            "Email is required — set field key to 'email' on your email input."
        )
    if not password:
        raise SignupValidationError(
            "Password is required — set field key to 'password' on your password input."
        )
    if len(password) < 8:
        raise SignupValidationError("Password must be at least 8 characters.")
    if not name:
        raise SignupValidationError(
            "Name is required — use field keys 'name', 'firstName', or 'lastName'."
        )

    if user_service.get_user_by_email(db, email):
        raise EmailAlreadyExistsError("An account with this email already exists.")

    user = user_service.create_user(
        db,
        organization_id=software.organization_id,
        data=UserCreate(
            name=name,
            email=email,
            mobile=user_fields.get("mobile"),
            password=password,
            role=UserRole.MEMBER,
            status=UserStatus.ACTIVE,
        ),
        actor_role=None,
    )

    user_profile_service.upsert_profile(
        db,
        user_id=user.id,
        organization_id=software.organization_id,
        software_id=data.software_id,
        page_id=data.page_id,
        fields=profile_fields,
    )

    tokens = _issue_tokens(db, user)
    return AppSignupResponse(user=user, tokens=tokens, profile=profile_fields)


def login(db: Database, data: LoginRequest) -> TokenResponse:
    doc = user_service.get_user_by_email(db, data.email)
    if doc is None or not verify_password(data.password, doc["password_hash"]):
        raise InvalidCredentialsError("Invalid email or password")

    user = _user_from_doc(doc)
    if user.status != UserStatus.ACTIVE:
        raise InactiveUserError("User account is inactive")

    return _issue_tokens(db, user)


def get_me(db: Database, user_id: str) -> MeResponse:
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise InvalidCredentialsError("User not found")

    organization = organization_service.get_organization(db, user.organization_id)
    if organization is None:
        raise InvalidCredentialsError("Organization not found")

    return MeResponse(
        user=user,
        organization=OrganizationSummary(id=organization.id, name=organization.name),
    )


def logout(db: Database, refresh_token: str) -> None:
    from app.core.security import safe_decode_token

    payload = safe_decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        return
    jti = payload.get("jti")
    if jti:
        user_service.revoke_refresh_token(db, jti)


def _issue_tokens(db: Database, user: UserRead) -> TokenResponse:
    access_token = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role.value,
    )
    refresh_token, jti, expires_at = create_refresh_token(user_id=user.id)
    user_service.store_refresh_token(db, user_id=user.id, jti=jti, expires_at=expires_at)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def issue_tokens_for_user(db: Database, user: UserRead) -> TokenResponse:
    """Public helper for OAuth and other alternate login paths."""
    return _issue_tokens(db, user)


def _user_from_doc(doc: dict) -> UserRead:
    public = doc_to_dict(doc)
    public.pop("password_hash", None)
    return UserRead.model_validate(public)
