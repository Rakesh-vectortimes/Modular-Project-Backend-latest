"""Auto-creates and maintains a MongoDB collection per page's form.

See design doc §6. When a page's layout is saved (`page_layout_service.replace_page_layout`),
`sync_page_schema` walks the saved tree, finds every node whose component_type is
marked `is_input` in `component_definitions`, and:
  - Builds a field manifest (stored in `page_data_schemas`, one doc per page).
  - Creates the page's Mongo collection (name: `page_data_<page_id>`) the first
    time it gets an input field, with a $jsonSchema validator reflecting the
    field types — or updates the validator via collMod if fields changed.
  - Soft-deletes (renames, never drops) the collection if a page's last input
    field is removed, or when the page itself is deleted.

Pages with zero input components never get a collection — this is intentional.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.database import Database
from pymongo.errors import OperationFailure

from app.db.mongo import utcnow
from app.services.field_mapper import is_sensitive_field_key
from app.schemas.page_data import (
    PageDataFieldSpec,
    PageDataSchemaRead,
    SubmissionListRead,
    SubmissionRead,
)

_BSON_TYPES: dict[str, list[str] | str] = {
    "string": "string",
    "number": ["double", "int", "long"],
    "boolean": "bool",
    "array": "array",
}


class PageHasNoDataCollectionError(Exception):
    pass


def _collection_name(page_id: str) -> str:
    return f"page_data_{page_id}"


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "field"


def _resolve_data_type(
    component_type: str, props: dict[str, Any], input_types: dict[str, str]
) -> str:
    """Prefer per-field inputType for generic user_input; else component default."""
    if component_type == "user_input":
        input_type = str(props.get("inputType") or "text").lower()
        if input_type == "number":
            return "number"
        if input_type in ("checkbox", "toggle"):
            return "boolean"
        if input_type == "file" and bool(props.get("multiple")):
            return "array"
        return "string"
    return input_types.get(component_type, "string")


def _extract_fields(
    nodes: list[dict[str, Any]], input_types: dict[str, str]
) -> list[PageDataFieldSpec]:
    fields: list[PageDataFieldSpec] = []
    seen_keys: set[str] = set()

    def visit(items: list[dict[str, Any]]) -> None:
        for node in items:
            component_type = node.get("component_type")
            if component_type in input_types:
                props = node.get("props") or {}
                label = str(props.get("label") or component_type)
                key = str(props.get("fieldKey") or "").strip() or _slugify(label)

                if is_sensitive_field_key(key):
                    visit(node.get("children") or [])
                    continue

                # de-dupe: two fields can't share a key within one page
                base_key = key
                suffix = 2
                while key in seen_keys:
                    key = f"{base_key}_{suffix}"
                    suffix += 1
                seen_keys.add(key)

                fields.append(
                    PageDataFieldSpec(
                        key=key,
                        label=label,
                        component_type=component_type,
                        data_type=_resolve_data_type(component_type, props, input_types),
                        required=bool(props.get("required")),
                        unique=bool(props.get("unique")),
                    )
                )
            visit(node.get("children") or [])

    visit(nodes)
    return fields


def _build_validator(fields: list[PageDataFieldSpec]) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "submitted_at": {"bsonType": "date"},
        "submitted_by": {"bsonType": ["string", "null"]},
    }
    required = ["submitted_at"]

    for field in fields:
        properties[field.key] = {"bsonType": [_BSON_TYPES.get(field.data_type, "string"), "null"]}
        if field.required:
            required.append(field.key)

    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": required,
            "properties": properties,
        }
    }


def _ensure_collection(
    db: Database, name: str, validator: dict[str, Any], unique_keys: list[str]
) -> None:
    if name in db.list_collection_names():
        try:
            db.command("collMod", name, validator=validator, validationLevel="moderate")
        except OperationFailure:
            # Best-effort — an existing collection that can't be modified (e.g.
            # permissions) shouldn't block saving the page layout itself.
            pass
    else:
        db.create_collection(name, validator=validator, validationLevel="moderate")
        db[name].create_index("submitted_at")

    for key in unique_keys:
        db[name].create_index(key, unique=True, sparse=True)


def sync_page_schema(
    db: Database,
    page_id: str,
    layout_tree: list[dict[str, Any]],
    input_types: dict[str, str],
) -> PageDataSchemaRead:
    fields = _extract_fields(layout_tree, input_types)
    collection_name = _collection_name(page_id)

    if not fields:
        # No more input fields on this page — soft-delete any existing collection.
        existing = db.page_data_schemas.find_one({"page_id": page_id})
        if existing and existing.get("collection_name"):
            old_name = existing["collection_name"]
            if old_name in db.list_collection_names():
                db[old_name].rename(f"__deleted__{old_name}", dropTarget=True)
        db.page_data_schemas.update_one(
            {"page_id": page_id},
            {
                "$set": {
                    "page_id": page_id,
                    "collection_name": None,
                    "fields": [],
                    "updated_at": utcnow(),
                }
            },
            upsert=True,
        )
        return PageDataSchemaRead(page_id=page_id, collection_name=None, fields=[], updated_at=utcnow())

    unique_keys = [f.key for f in fields if f.unique]
    _ensure_collection(db, collection_name, _build_validator(fields), unique_keys)

    db.page_data_schemas.update_one(
        {"page_id": page_id},
        {
            "$set": {
                "page_id": page_id,
                "collection_name": collection_name,
                "fields": [f.model_dump() for f in fields],
                "updated_at": utcnow(),
            }
        },
        upsert=True,
    )

    return PageDataSchemaRead(
        page_id=page_id,
        collection_name=collection_name,
        fields=fields,
        updated_at=utcnow(),
    )


def get_page_data_schema(db: Database, page_id: str) -> PageDataSchemaRead:
    doc = db.page_data_schemas.find_one({"page_id": page_id})
    if not doc:
        return PageDataSchemaRead(page_id=page_id, collection_name=None, fields=[])
    return PageDataSchemaRead(
        page_id=page_id,
        collection_name=doc.get("collection_name"),
        fields=[PageDataFieldSpec.model_validate(f) for f in doc.get("fields", [])],
        updated_at=doc.get("updated_at"),
    )


def insert_submission(
    db: Database, page_id: str, values: dict[str, Any], submitted_by: str | None
) -> SubmissionRead:
    schema = get_page_data_schema(db, page_id)
    if not schema.collection_name:
        raise PageHasNoDataCollectionError(
            f"Page {page_id} has no data-capturing fields — nothing to submit."
        )

    allowed_keys = {f.key for f in schema.fields}
    clean_values = {k: v for k, v in values.items() if k in allowed_keys}

    doc = {
        "page_id": page_id,
        **clean_values,
        "submitted_at": utcnow(),
        "submitted_by": submitted_by,
    }
    result = db[schema.collection_name].insert_one(doc)
    doc["_id"] = result.inserted_id

    return SubmissionRead(
        id=str(doc["_id"]),
        page_id=page_id,
        values=clean_values,
        submitted_at=doc["submitted_at"],
        submitted_by=submitted_by,
    )


def list_submissions(
    db: Database, page_id: str, skip: int = 0, limit: int = 50
) -> SubmissionListRead:
    schema = get_page_data_schema(db, page_id)
    if not schema.collection_name:
        return SubmissionListRead(total=0, items=[])

    collection = db[schema.collection_name]
    total = collection.count_documents({})
    docs = list(
        collection.find().sort("submitted_at", -1).skip(skip).limit(limit)
    )

    field_keys = {f.key for f in schema.fields}
    items = [
        SubmissionRead(
            id=str(doc["_id"]),
            page_id=page_id,
            values={k: v for k, v in doc.items() if k in field_keys},
            submitted_at=doc.get("submitted_at") or datetime.min,
            submitted_by=doc.get("submitted_by"),
        )
        for doc in docs
    ]
    return SubmissionListRead(total=total, items=items)


def soft_delete_page_collection(db: Database, page_id: str) -> None:
    """Called when a page is deleted — renames (never drops) its data collection."""
    existing = db.page_data_schemas.find_one({"page_id": page_id})
    if existing and existing.get("collection_name"):
        name = existing["collection_name"]
        if name in db.list_collection_names():
            db[name].rename(f"__deleted__{name}", dropTarget=True)
    db.page_data_schemas.delete_one({"page_id": page_id})
