"""Map builder `fieldKey` values to user account + profile fields."""

from __future__ import annotations

from typing import Any

# Keys that map to core `users` collection fields (never stored in page_data).
USER_ACCOUNT_KEYS = frozenset(
    {
        "email",
        "password",
        "name",
        "full_name",
        "fullname",
        "mobile",
        "phone",
        "phone_number",
        "phonenumber",
    }
)

# Keys excluded from page_data collections (security).
SENSITIVE_PAGE_DATA_KEYS = frozenset({"password", "password_confirm", "confirm_password"})

_NAME_KEYS = frozenset({"name", "full_name", "fullname"})
_EMAIL_KEYS = frozenset({"email"})
_PASSWORD_KEYS = frozenset({"password"})
_MOBILE_KEYS = frozenset({"mobile", "phone", "phone_number", "phonenumber"})
_FIRST_NAME_KEYS = frozenset({"firstname", "first_name", "firstName"})
_LAST_NAME_KEYS = frozenset({"lastname", "last_name", "lastName"})


def _norm_key(key: str) -> str:
    return key.strip()


def _lower(key: str) -> str:
    return _norm_key(key).lower()


def is_sensitive_field_key(key: str) -> bool:
    return _lower(key) in SENSITIVE_PAGE_DATA_KEYS


def map_signup_values(values: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split form values into user-account fields and extended profile fields.

    Returns `(user_fields, profile_fields)` where user_fields contains
    `email`, `password`, `name`, `mobile` when present.
    """
    user_fields: dict[str, Any] = {}
    profile: dict[str, Any] = {}

    for raw_key, raw_value in values.items():
        if raw_value is None:
            continue
        value = raw_value if isinstance(raw_value, str) else str(raw_value)
        value = value.strip()
        if not value:
            continue

        key = _norm_key(raw_key)
        lower = _lower(key)

        if lower in _EMAIL_KEYS:
            user_fields["email"] = value
        elif lower in _PASSWORD_KEYS:
            user_fields["password"] = value
        elif lower in _NAME_KEYS:
            user_fields["name"] = value
        elif lower in _MOBILE_KEYS:
            user_fields["mobile"] = value
        elif lower in _FIRST_NAME_KEYS:
            profile["firstName"] = value
        elif lower in _LAST_NAME_KEYS:
            profile["lastName"] = value
        else:
            profile[key] = value

    if not user_fields.get("name"):
        parts = [profile.get("firstName"), profile.get("lastName")]
        combined = " ".join(p for p in parts if p).strip()
        if combined:
            user_fields["name"] = combined

    if not user_fields.get("name") and user_fields.get("email"):
        user_fields["name"] = user_fields["email"].split("@")[0]

    return user_fields, profile


def map_login_values(
    values: dict[str, Any],
    *,
    email_field_key: str = "email",
    password_field_key: str = "password",
) -> dict[str, str]:
    """Extract email/password from form values using configured field keys."""
    email = values.get(email_field_key)
    password = values.get(password_field_key)

    if email is None:
        for key, val in values.items():
            if _lower(key) in _EMAIL_KEYS:
                email = val
                break
    if password is None:
        for key, val in values.items():
            if _lower(key) in _PASSWORD_KEYS:
                password = val
                break

    return {
        "email": str(email or "").strip(),
        "password": str(password or ""),
    }
