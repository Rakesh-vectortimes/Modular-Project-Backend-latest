from datetime import datetime
from typing import Any

from bson import ObjectId


def str_id(doc: dict[str, Any] | None) -> str | None:
    if doc is None:
        return None
    return str(doc["_id"])


def doc_to_dict(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None

    result = dict(doc)
    result["id"] = str(result.pop("_id"))
    return result


def docs_to_dicts(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [doc_to_dict(doc) for doc in docs]  # type: ignore[misc]


def prepare_insert(document: dict[str, Any]) -> dict[str, Any]:
    now = datetime.utcnow()
    payload = dict(document)
    payload.pop("id", None)
    payload.setdefault("created_at", now)
    payload.setdefault("updated_at", now)
    return payload


def prepare_update(fields: dict[str, Any]) -> dict[str, Any]:
    payload = dict(fields)
    payload.pop("id", None)
    payload.pop("_id", None)
    payload.pop("created_at", None)
    payload["updated_at"] = datetime.utcnow()
    return payload
