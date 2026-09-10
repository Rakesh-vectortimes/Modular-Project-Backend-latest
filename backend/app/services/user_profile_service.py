"""Extended signup/profile fields keyed by user (address, pincode, firstName, …)."""

from __future__ import annotations

from typing import Any

from pymongo.database import Database

from app.db.mongo import utcnow
from app.db.serialize import prepare_insert, prepare_update


def upsert_profile(
    db: Database,
    *,
    user_id: str,
    organization_id: str,
    software_id: str | None,
    page_id: str | None,
    fields: dict[str, Any],
) -> None:
    if not fields:
        return

    now = utcnow()
    existing = db.user_profiles.find_one({"user_id": user_id})
    if existing:
        merged = {**(existing.get("fields") or {}), **fields}
        db.user_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": prepare_update(
                    {
                        "fields": merged,
                        "software_id": software_id,
                        "page_id": page_id,
                        "updated_at": now,
                    }
                )
            },
        )
        return

    db.user_profiles.insert_one(
        prepare_insert(
            {
                "user_id": user_id,
                "organization_id": organization_id,
                "software_id": software_id,
                "page_id": page_id,
                "fields": fields,
            }
        )
    )


def get_profile_fields(db: Database, user_id: str) -> dict[str, Any]:
    doc = db.user_profiles.find_one({"user_id": user_id})
    if not doc:
        return {}
    return dict(doc.get("fields") or {})
