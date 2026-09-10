from pymongo import ReturnDocument
from pymongo.database import Database

from app.db.mongo import oid
from app.db.serialize import doc_to_dict, docs_to_dicts, prepare_insert, prepare_update
from app.schemas.software import SoftwareCreate, SoftwareRead, SoftwareUpdate


def list_software(
    db: Database, *, organization_id: str, skip: int = 0, limit: int = 100
) -> list[SoftwareRead]:
    docs = list(
        db.software.find({"organization_id": organization_id})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [SoftwareRead.model_validate(doc) for doc in docs_to_dicts(docs)]


def get_software(db: Database, software_id: str, organization_id: str | None = None) -> SoftwareRead | None:
    query: dict = {"_id": oid(software_id)}
    if organization_id is not None:
        query["organization_id"] = organization_id
    doc = db.software.find_one(query)
    parsed = doc_to_dict(doc)
    return SoftwareRead.model_validate(parsed) if parsed else None


def create_software(
    db: Database, *, organization_id: str, owner_id: str, data: SoftwareCreate
) -> SoftwareRead:
    payload = prepare_insert(
        {
            "organization_id": organization_id,
            "owner_id": owner_id,
            "name": data.name,
            "description": data.description,
            "category": data.category,
        }
    )
    result = db.software.insert_one(payload)
    doc = db.software.find_one({"_id": result.inserted_id})
    return SoftwareRead.model_validate(doc_to_dict(doc))


def update_software(
    db: Database, software_id: str, organization_id: str, data: SoftwareUpdate
) -> SoftwareRead | None:
    update_data = prepare_update(data.model_dump(exclude_unset=True))
    doc = db.software.find_one_and_update(
        {"_id": oid(software_id), "organization_id": organization_id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )
    parsed = doc_to_dict(doc)
    return SoftwareRead.model_validate(parsed) if parsed else None


def delete_software(db: Database, software_id: str, organization_id: str) -> bool:
    existing = db.software.find_one({"_id": oid(software_id), "organization_id": organization_id})
    if existing is None:
        return False

    page_ids = [
        str(page["_id"])
        for page in db.pages.find({"software_id": software_id, "organization_id": organization_id}, {"_id": 1})
    ]
    if page_ids:
        db.page_components.delete_many({"page_id": {"$in": page_ids}})
    db.pages.delete_many({"software_id": software_id, "organization_id": organization_id})
    result = db.software.delete_one({"_id": oid(software_id), "organization_id": organization_id})
    return result.deleted_count > 0
