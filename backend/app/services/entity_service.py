"""Reusable entities (tables) shared across the pages of one app.

An *entity* is a named table (e.g. "Customers"). Every page's form is bound to
an entity by name; pages that share the same entity name *within one software*
are backed by the same Mongo collection `entity_data_<entity_id>`. If a page has
no `entity_name`, it defaults to the page's own name — so by default each page
still gets its own table and pre-entity behaviour is preserved.

Fields are still auto-inferred from the input components a user drops. On every
layout save the bound entity's field manifest is recomputed as the **union** of
the input fields across every page bound to that entity, so the table stays
accurate as pages add or remove inputs. See design doc: Reusable Entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.database import Database
from pymongo.errors import OperationFailure

from app.db.mongo import new_object_id, oid, utcnow
from app.schemas.entity import EntityRead, RecordListRead, RecordRead
from app.schemas.page_data import PageDataFieldSpec, PageDataSchemaRead
from app.services import component_definition_service
from app.services.field_mapper import is_sensitive_field_key

_BSON_TYPES: dict[str, list[str] | str] = {
    "string": "string",
    "number": ["double", "int", "long"],
    "boolean": "bool",
    "array": "array",
}


class PageHasNoDataCollectionError(Exception):
    pass


class EntityHasNoDataCollectionError(Exception):
    pass


# --------------------------------------------------------------------------- #
# Field extraction (from a page's layout tree)
# --------------------------------------------------------------------------- #

def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in (value or "")).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "entity"


def _slugify_field(value: str) -> str:
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


def extract_fields(
    nodes: list[dict[str, Any]], input_types: dict[str, str]
) -> list[PageDataFieldSpec]:
    """Walk a layout tree and return the field spec for every input component."""
    fields: list[PageDataFieldSpec] = []
    seen_keys: set[str] = set()

    def visit(items: list[dict[str, Any]]) -> None:
        for node in items:
            component_type = node.get("component_type")
            if component_type in input_types:
                props = node.get("props") or {}
                label = str(props.get("label") or component_type)
                key = str(props.get("fieldKey") or "").strip() or _slugify_field(label)

                if is_sensitive_field_key(key):
                    visit(node.get("children") or [])
                    continue

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


def _merge_fields(field_groups: list[list[PageDataFieldSpec]]) -> list[PageDataFieldSpec]:
    """Union fields by key across all pages bound to an entity.

    - data_type: first non-`string` type wins.
    - unique: True if unique on any contributing page.
    - required: preserved on the spec (client-enforced per form; NOT put in the
      collection validator — different forms over one table include different
      field subsets).
    """
    merged: dict[str, PageDataFieldSpec] = {}
    for group in field_groups:
        for field in group:
            existing = merged.get(field.key)
            if existing is None:
                merged[field.key] = field.model_copy()
                continue
            if existing.data_type == "string" and field.data_type != "string":
                existing.data_type = field.data_type
            existing.unique = existing.unique or field.unique
            existing.required = existing.required or field.required
    return list(merged.values())


# --------------------------------------------------------------------------- #
# Collection management
# --------------------------------------------------------------------------- #

def _collection_name(entity_id: str) -> str:
    return f"entity_data_{entity_id}"


def _build_validator(fields: list[PageDataFieldSpec]) -> dict[str, Any]:
    """Only `submitted_at` is globally required — see `_merge_fields` docstring."""
    properties: dict[str, Any] = {
        "page_id": {"bsonType": ["string", "null"]},
        "submitted_at": {"bsonType": "date"},
        "submitted_by": {"bsonType": ["string", "null"]},
    }
    for field in fields:
        properties[field.key] = {
            "bsonType": [_BSON_TYPES.get(field.data_type, "string"), "null"]
        }
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["submitted_at"],
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
            pass
    else:
        db.create_collection(name, validator=validator, validationLevel="moderate")
        db[name].create_index("submitted_at")

    for key in unique_keys:
        db[name].create_index(key, unique=True, sparse=True)


def _soft_delete_collection(db: Database, name: str | None) -> None:
    if name and name in db.list_collection_names():
        db[name].rename(f"__deleted__{name}", dropTarget=True)


# --------------------------------------------------------------------------- #
# Entity resolution
# --------------------------------------------------------------------------- #

def _entity_name_for_page(page: dict[str, Any]) -> str:
    raw = str(page.get("entity_name") or "").strip()
    return raw or str(page.get("name") or "").strip() or "data"


def resolve_entity_for_page(
    db: Database, page: dict[str, Any], *, create: bool = True
) -> dict[str, Any] | None:
    name = _entity_name_for_page(page)
    slug = slugify(name)
    software_id = page["software_id"]

    doc = db.entities.find_one({"software_id": software_id, "slug": slug})
    if doc is not None:
        return doc
    if not create:
        return None

    now = utcnow()
    entity_doc = {
        "_id": new_object_id(),
        "organization_id": page["organization_id"],
        "software_id": software_id,
        "name": name,
        "slug": slug,
        "collection_name": None,
        "fields": [],
        "created_at": now,
        "updated_at": now,
    }
    db.entities.insert_one(entity_doc)
    return entity_doc


def _bound_page_ids(db: Database, entity: dict[str, Any]) -> list[str]:
    """Page ids in the same software whose resolved entity slug matches."""
    slug = entity["slug"]
    ids: list[str] = []
    for page in db.pages.find({"software_id": entity["software_id"]}):
        if slugify(_entity_name_for_page(page)) == slug:
            ids.append(str(page["_id"]))
    return ids


def _fields_for_page(db: Database, page_id: str, input_types: dict[str, str]) -> list[PageDataFieldSpec]:
    from app.services.page_layout_service import build_tree_from_flat

    components = list(db.page_components.find({"page_id": page_id}))
    tree = build_tree_from_flat(components)
    tree_dicts = [node.model_dump() for node in tree]
    return extract_fields(tree_dicts, input_types)


# --------------------------------------------------------------------------- #
# Schema sync
# --------------------------------------------------------------------------- #

def recompute_entity_schema(db: Database, entity_id: str) -> EntityRead:
    entity = db.entities.find_one({"_id": oid(entity_id)})
    if entity is None:
        raise EntityHasNoDataCollectionError(f"Entity {entity_id} not found")

    input_types = component_definition_service.get_input_type_data_types(db)
    page_ids = _bound_page_ids(db, entity)

    field_groups = [_fields_for_page(db, pid, input_types) for pid in page_ids]
    fields = _merge_fields(field_groups)

    if not fields:
        _soft_delete_collection(db, entity.get("collection_name"))
        db.entities.update_one(
            {"_id": entity["_id"]},
            {"$set": {"collection_name": None, "fields": [], "updated_at": utcnow()}},
        )
        return _entity_read(db.entities.find_one({"_id": entity["_id"]}))

    collection_name = _collection_name(str(entity["_id"]))
    unique_keys = [f.key for f in fields if f.unique]
    _ensure_collection(db, collection_name, _build_validator(fields), unique_keys)

    db.entities.update_one(
        {"_id": entity["_id"]},
        {
            "$set": {
                "collection_name": collection_name,
                "fields": [f.model_dump() for f in fields],
                "updated_at": utcnow(),
            }
        },
    )
    return _entity_read(db.entities.find_one({"_id": entity["_id"]}))


def sync_page_entity(db: Database, page_id: str) -> PageDataSchemaRead:
    """Called on layout save — resolves the page's entity and recomputes it."""
    page = db.pages.find_one({"_id": oid(page_id)})
    if page is None:
        return PageDataSchemaRead(page_id=page_id, collection_name=None, fields=[])

    entity = resolve_entity_for_page(db, page, create=True)
    entity_read = recompute_entity_schema(db, str(entity["_id"]))
    return _schema_read_from_entity(page_id, entity_read)


def handle_page_meta_change(
    db: Database, old_page: dict[str, Any], new_page: dict[str, Any]
) -> None:
    """Recompute the entities affected by a page rename or entity rebinding.

    Resolution is name-based at request time, so reads/writes already follow the
    new binding immediately; this just keeps the stored field manifests accurate.
    """
    seen: set[str] = set()
    for page in (old_page, new_page):
        entity = resolve_entity_for_page(db, page, create=False)
        if entity is not None and str(entity["_id"]) not in seen:
            seen.add(str(entity["_id"]))
            recompute_entity_schema(db, str(entity["_id"]))


def on_page_deleted(db: Database, page: dict[str, Any]) -> None:
    """Recompute the (former) entity so the deleted page's fields drop out.

    The collection is never dropped — if the entity is now empty it is soft
    deleted (renamed) by `recompute_entity_schema`.
    """
    entity = resolve_entity_for_page(db, page, create=False)
    if entity is not None:
        recompute_entity_schema(db, str(entity["_id"]))


# --------------------------------------------------------------------------- #
# Reads / records
# --------------------------------------------------------------------------- #

def _entity_read(doc: dict[str, Any] | None) -> EntityRead:
    assert doc is not None
    return EntityRead(
        id=str(doc["_id"]),
        organization_id=doc["organization_id"],
        software_id=doc["software_id"],
        name=doc["name"],
        slug=doc["slug"],
        collection_name=doc.get("collection_name"),
        fields=[PageDataFieldSpec.model_validate(f) for f in doc.get("fields", [])],
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


def _schema_read_from_entity(page_id: str, entity: EntityRead) -> PageDataSchemaRead:
    return PageDataSchemaRead(
        page_id=page_id,
        collection_name=entity.collection_name,
        fields=entity.fields,
        entity_id=entity.id,
        entity_name=entity.name,
        updated_at=entity.updated_at,
    )


def get_schema_for_page(db: Database, page_id: str) -> PageDataSchemaRead:
    page = db.pages.find_one({"_id": oid(page_id)})
    if page is None:
        return PageDataSchemaRead(page_id=page_id, collection_name=None, fields=[])
    entity = resolve_entity_for_page(db, page, create=False)
    if entity is None:
        return PageDataSchemaRead(page_id=page_id, collection_name=None, fields=[])
    return _schema_read_from_entity(page_id, _entity_read(entity))


def list_entities(db: Database, software_id: str, organization_id: str) -> list[EntityRead]:
    docs = db.entities.find(
        {"software_id": software_id, "organization_id": organization_id}
    ).sort("name", 1)
    return [_entity_read(doc) for doc in docs]


def get_entity(db: Database, entity_id: str, organization_id: str | None = None) -> EntityRead | None:
    query: dict[str, Any] = {"_id": oid(entity_id)}
    if organization_id is not None:
        query["organization_id"] = organization_id
    doc = db.entities.find_one(query)
    return _entity_read(doc) if doc else None


def _insert_record(
    db: Database, entity: dict[str, Any], values: dict[str, Any], submitted_by: str | None,
    page_id: str | None = None,
) -> RecordRead:
    collection_name = entity.get("collection_name")
    if not collection_name:
        raise EntityHasNoDataCollectionError(
            f"Entity '{entity.get('name')}' has no data-capturing fields yet."
        )

    allowed = {f["key"] for f in entity.get("fields", [])}
    clean = {k: v for k, v in values.items() if k in allowed}

    doc = {
        "page_id": page_id,
        **clean,
        "submitted_at": utcnow(),
        "submitted_by": submitted_by,
    }
    result = db[collection_name].insert_one(doc)
    return RecordRead(
        id=str(result.inserted_id),
        entity_id=str(entity["_id"]),
        values=clean,
        submitted_at=doc["submitted_at"],
        submitted_by=submitted_by,
    )


def insert_record(
    db: Database, entity_id: str, values: dict[str, Any], submitted_by: str | None,
    organization_id: str | None = None,
) -> RecordRead:
    query: dict[str, Any] = {"_id": oid(entity_id)}
    if organization_id is not None:
        query["organization_id"] = organization_id
    entity = db.entities.find_one(query)
    if entity is None:
        raise EntityHasNoDataCollectionError(f"Entity {entity_id} not found")
    return _insert_record(db, entity, values, submitted_by)


def insert_record_for_page(
    db: Database, page_id: str, values: dict[str, Any], submitted_by: str | None
) -> RecordRead:
    page = db.pages.find_one({"_id": oid(page_id)})
    if page is None:
        raise PageHasNoDataCollectionError(f"Page {page_id} not found")
    entity = resolve_entity_for_page(db, page, create=False)
    if entity is None or not entity.get("collection_name"):
        raise PageHasNoDataCollectionError(
            f"Page {page_id} has no data-capturing fields — nothing to submit."
        )
    return _insert_record(db, entity, values, submitted_by, page_id=page_id)


def _list_records(db: Database, entity: dict[str, Any], skip: int, limit: int) -> RecordListRead:
    collection_name = entity.get("collection_name")
    if not collection_name or collection_name not in db.list_collection_names():
        return RecordListRead(total=0, items=[])

    collection = db[collection_name]
    field_keys = {f["key"] for f in entity.get("fields", [])}
    total = collection.count_documents({})
    docs = list(collection.find().sort("submitted_at", -1).skip(skip).limit(limit))
    items = [
        RecordRead(
            id=str(doc["_id"]),
            entity_id=str(entity["_id"]),
            values={k: v for k, v in doc.items() if k in field_keys},
            submitted_at=doc.get("submitted_at") or datetime.min,
            submitted_by=doc.get("submitted_by"),
        )
        for doc in docs
    ]
    return RecordListRead(total=total, items=items)


def list_records(
    db: Database, entity_id: str, skip: int = 0, limit: int = 50,
    organization_id: str | None = None,
) -> RecordListRead:
    query: dict[str, Any] = {"_id": oid(entity_id)}
    if organization_id is not None:
        query["organization_id"] = organization_id
    entity = db.entities.find_one(query)
    if entity is None:
        return RecordListRead(total=0, items=[])
    return _list_records(db, entity, skip, limit)


def list_records_for_page(
    db: Database, page_id: str, skip: int = 0, limit: int = 50
) -> RecordListRead:
    page = db.pages.find_one({"_id": oid(page_id)})
    if page is None:
        return RecordListRead(total=0, items=[])
    entity = resolve_entity_for_page(db, page, create=False)
    if entity is None:
        return RecordListRead(total=0, items=[])
    return _list_records(db, entity, skip, limit)
