from pymongo.database import Database

from app.db.mongo import oid
from app.db.serialize import doc_to_dict, prepare_insert
from app.schemas.organization import OrganizationRead


def get_organization(db: Database, organization_id: str) -> OrganizationRead | None:
    doc = db.organizations.find_one({"_id": oid(organization_id)})
    parsed = doc_to_dict(doc)
    return OrganizationRead.model_validate(parsed) if parsed else None


def create_organization(db: Database, name: str) -> OrganizationRead:
    payload = prepare_insert({"name": name})
    result = db.organizations.insert_one(payload)
    doc = db.organizations.find_one({"_id": result.inserted_id})
    return OrganizationRead.model_validate(doc_to_dict(doc))
