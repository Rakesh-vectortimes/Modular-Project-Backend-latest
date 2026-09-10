from pymongo import ReturnDocument
from pymongo.database import Database

from app.db.mongo import oid
from app.db.serialize import doc_to_dict, docs_to_dicts, prepare_insert, prepare_update
from app.schemas.page import PageCreate, PageRead, PageUpdate
from app.services import page_data_schema_service


class SoftwareNotInOrganizationError(Exception):
    pass


def list_pages(
    db: Database, *, organization_id: str, software_id: str | None = None
) -> list[PageRead]:
    query: dict = {"organization_id": organization_id}
    if software_id is not None:
        query["software_id"] = software_id
    docs = list(db.pages.find(query).sort("created_at", 1))
    return [PageRead.model_validate(doc) for doc in docs_to_dicts(docs)]


def get_page(db: Database, page_id: str, organization_id: str | None = None) -> PageRead | None:
    query: dict = {"_id": oid(page_id)}
    if organization_id is not None:
        query["organization_id"] = organization_id
    doc = db.pages.find_one(query)
    parsed = doc_to_dict(doc)
    return PageRead.model_validate(parsed) if parsed else None


def create_page(db: Database, *, organization_id: str, data: PageCreate) -> PageRead:
    software = db.software.find_one({"_id": oid(data.software_id), "organization_id": organization_id})
    if software is None:
        raise SoftwareNotInOrganizationError("Software not found in organization")

    if data.is_default:
        _clear_default_for_software(db, data.software_id, organization_id)

    payload = prepare_insert(
        {
            "organization_id": organization_id,
            "software_id": data.software_id,
            "name": data.name,
            "is_default": data.is_default,
        }
    )
    result = db.pages.insert_one(payload)
    doc = db.pages.find_one({"_id": result.inserted_id})
    return PageRead.model_validate(doc_to_dict(doc))


def update_page(
    db: Database, page_id: str, organization_id: str, data: PageUpdate
) -> PageRead | None:
    existing = db.pages.find_one({"_id": oid(page_id), "organization_id": organization_id})
    if existing is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("is_default") is True and not existing.get("is_default"):
        _clear_default_for_software(db, existing["software_id"], organization_id)

    payload = prepare_update(update_data)
    doc = db.pages.find_one_and_update(
        {"_id": oid(page_id), "organization_id": organization_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER,
    )
    parsed = doc_to_dict(doc)
    return PageRead.model_validate(parsed) if parsed else None


def set_default_page(db: Database, page_id: str, organization_id: str) -> PageRead | None:
    existing = db.pages.find_one({"_id": oid(page_id), "organization_id": organization_id})
    if existing is None:
        return None

    _clear_default_for_software(db, existing["software_id"], organization_id)
    doc = db.pages.find_one_and_update(
        {"_id": oid(page_id), "organization_id": organization_id},
        {"$set": prepare_update({"is_default": True})},
        return_document=ReturnDocument.AFTER,
    )
    parsed = doc_to_dict(doc)
    return PageRead.model_validate(parsed) if parsed else None


def delete_page(db: Database, page_id: str, organization_id: str) -> bool:
    result = db.pages.delete_one({"_id": oid(page_id), "organization_id": organization_id})
    if result.deleted_count:
        db.page_components.delete_many({"page_id": page_id})
        # Soft-delete (rename, never drop) this page's auto-created data collection, if any.
        page_data_schema_service.soft_delete_page_collection(db, page_id)
    return result.deleted_count > 0


def get_default_page_for_software(
    db: Database, software_id: str, organization_id: str | None = None
) -> PageRead | None:
    query: dict = {"software_id": software_id, "is_default": True}
    if organization_id is not None:
        query["organization_id"] = organization_id
    doc = db.pages.find_one(query)
    parsed = doc_to_dict(doc)
    return PageRead.model_validate(parsed) if parsed else None


def _clear_default_for_software(db: Database, software_id: str, organization_id: str) -> None:
    db.pages.update_many(
        {"software_id": software_id, "organization_id": organization_id, "is_default": True},
        {"$set": prepare_update({"is_default": False})},
    )
