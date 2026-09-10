import secrets
from datetime import UTC, datetime

from pymongo import ReturnDocument
from pymongo.database import Database

from app.core.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.db.mongo import oid
from app.db.serialize import doc_to_dict, docs_to_dicts, prepare_insert, prepare_update
from app.schemas.user import CurrentUser, UserCreate, UserListResponse, UserRead, UserUpdate


class UserNotFoundError(Exception):
    pass


class EmailAlreadyExistsError(Exception):
    pass


class RolePermissionError(Exception):
    pass


class InactiveOAuthUserError(Exception):
    pass


def get_user_by_id(db: Database, user_id: str) -> UserRead | None:
    doc = db.users.find_one({"_id": oid(user_id)})
    parsed = doc_to_dict(doc)
    return UserRead.model_validate(parsed) if parsed else None


def get_user_by_email(db: Database, email: str) -> dict | None:
    return db.users.find_one({"email": email.lower()})


def get_user_by_google_sub(db: Database, google_sub: str) -> dict | None:
    return db.users.find_one({"google_sub": google_sub})


def find_or_create_google_user(
    db: Database,
    *,
    organization_id: str,
    email: str,
    name: str,
    google_sub: str,
) -> UserRead:
    existing = get_user_by_google_sub(db, google_sub)
    if existing is None:
        existing = get_user_by_email(db, email)

    if existing is not None:
        user = UserRead.model_validate(doc_to_dict(existing))
        if user.status != UserStatus.ACTIVE:
            raise InactiveOAuthUserError("User account is inactive")

        updates: dict = {}
        if not existing.get("google_sub"):
            updates["google_sub"] = google_sub
        if existing.get("auth_provider") != "google":
            updates["auth_provider"] = "google"
        if updates:
            db.users.update_one({"_id": oid(user.id)}, {"$set": prepare_update(updates)})
        return user

    import secrets

    from app.core.security import hash_password

    payload = prepare_insert(
        {
            "organization_id": organization_id,
            "name": name,
            "email": email.lower(),
            "mobile": None,
            "password_hash": hash_password(secrets.token_urlsafe(32)),
            "role": UserRole.MEMBER.value,
            "status": UserStatus.ACTIVE.value,
            "auth_provider": "google",
            "google_sub": google_sub,
        }
    )
    result = db.users.insert_one(payload)
    doc = db.users.find_one({"_id": result.inserted_id})
    return UserRead.model_validate(doc_to_dict(doc))


def get_user_in_organization(db: Database, user_id: str, organization_id: str) -> UserRead | None:
    doc = db.users.find_one({"_id": oid(user_id), "organization_id": organization_id})
    parsed = doc_to_dict(doc)
    return UserRead.model_validate(parsed) if parsed else None


def to_current_user(user: UserRead) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        organization_id=user.organization_id,
        name=user.name,
        email=user.email,
        mobile=user.mobile,
        role=user.role,
        status=user.status,
    )


def create_user(
    db: Database,
    *,
    organization_id: str,
    data: UserCreate,
    actor_role: UserRole | None = None,
) -> UserRead:
    if actor_role is not None:
        assert_role_assignment_allowed(actor_role, data.role)

    if get_user_by_email(db, data.email):
        raise EmailAlreadyExistsError(f"Email '{data.email}' is already registered")

    payload = prepare_insert(
        {
            "organization_id": organization_id,
            "name": data.name,
            "email": data.email.lower(),
            "mobile": data.mobile,
            "password_hash": hash_password(data.password),
            "role": data.role.value,
            "status": data.status.value,
        }
    )
    result = db.users.insert_one(payload)
    doc = db.users.find_one({"_id": result.inserted_id})
    return UserRead.model_validate(doc_to_dict(doc))


def list_users(
    db: Database,
    *,
    organization_id: str,
    search: str | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> UserListResponse:
    query: dict = {"organization_id": organization_id}

    if role is not None:
        query["role"] = role.value
    if status is not None:
        query["status"] = status.value
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"mobile": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    skip = max(page - 1, 0) * page_size
    total = db.users.count_documents(query)
    docs = list(db.users.find(query).sort("created_at", -1).skip(skip).limit(page_size))
    items = [UserRead.model_validate(doc) for doc in docs_to_dicts(docs)]
    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


def update_user(
    db: Database,
    *,
    user_id: str,
    organization_id: str,
    data: UserUpdate,
    actor_role: UserRole,
) -> UserRead | None:
    existing = db.users.find_one({"_id": oid(user_id), "organization_id": organization_id})
    if existing is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"]:
        update_data["email"] = update_data["email"].lower()
        other = db.users.find_one(
            {"email": update_data["email"], "_id": {"$ne": oid(user_id)}}
        )
        if other:
            raise EmailAlreadyExistsError(f"Email '{update_data['email']}' is already registered")

    if "role" in update_data and update_data["role"] is not None:
        new_role = update_data["role"]
        assert_role_assignment_allowed(actor_role, new_role)
        if existing.get("role") == UserRole.SUPER_ADMIN.value and actor_role != UserRole.SUPER_ADMIN:
            raise RolePermissionError("Only super_admin can modify another super_admin")
        update_data["role"] = new_role.value

    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value

    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    payload = prepare_update(update_data)
    doc = db.users.find_one_and_update(
        {"_id": oid(user_id), "organization_id": organization_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER,
    )
    parsed = doc_to_dict(doc)
    return UserRead.model_validate(parsed) if parsed else None


def delete_user(
    db: Database,
    *,
    user_id: str,
    organization_id: str,
    actor_id: str,
    actor_role: UserRole,
) -> bool:
    if user_id == actor_id:
        raise RolePermissionError("You cannot delete your own account")

    existing = db.users.find_one({"_id": oid(user_id), "organization_id": organization_id})
    if existing is None:
        return False

    if existing.get("role") == UserRole.SUPER_ADMIN.value and actor_role != UserRole.SUPER_ADMIN:
        raise RolePermissionError("Only super_admin can delete another super_admin")

    result = db.users.delete_one({"_id": oid(user_id), "organization_id": organization_id})
    return result.deleted_count > 0


def assert_role_assignment_allowed(actor_role: UserRole, target_role: UserRole) -> None:
    if target_role == UserRole.SUPER_ADMIN and actor_role != UserRole.SUPER_ADMIN:
        raise RolePermissionError("Only super_admin can assign the super_admin role")
    if actor_role == UserRole.MEMBER:
        raise RolePermissionError("Members cannot manage users")


def store_refresh_token(db: Database, *, user_id: str, jti: str, expires_at: datetime) -> None:
    db.refresh_tokens.insert_one(
        prepare_insert(
            {
                "user_id": user_id,
                "jti": jti,
                "expires_at": expires_at,
                "revoked": False,
            }
        )
    )


def revoke_refresh_token(db: Database, jti: str) -> bool:
    result = db.refresh_tokens.update_one(
        {"jti": jti, "revoked": False},
        {"$set": prepare_update({"revoked": True, "revoked_at": datetime.now(UTC)})},
    )
    return result.modified_count > 0


def is_refresh_token_revoked(db: Database, jti: str) -> bool:
    doc = db.refresh_tokens.find_one({"jti": jti})
    if doc is None:
        return True
    if doc.get("revoked"):
        return True
    expires_at = doc.get("expires_at")
    if expires_at and expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        return True
    return False
