from collections.abc import Generator
from datetime import UTC, datetime

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        # Fail fast when Mongo is down so request threads don't pile up and
        # freeze the whole API (uploads, health, etc.).
        _client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5_000,
            connectTimeoutMS=5_000,
            socketTimeoutMS=10_000,
        )
    return _client


def get_database() -> Database:
    return get_client()[settings.MONGODB_DB_NAME]


def get_db() -> Generator[Database, None, None]:
    yield get_database()


def init_indexes() -> None:
    db = get_database()

    db.organizations.create_index("name")
    db.organizations.create_index("created_at")

    db.users.create_index("email", unique=True)
    db.users.create_index("organization_id")
    db.users.create_index([("organization_id", 1), ("role", 1)])
    db.users.create_index([("organization_id", 1), ("status", 1)])
    db.users.create_index([("organization_id", 1), ("created_at", -1)])

    db.refresh_tokens.create_index("jti", unique=True)
    db.refresh_tokens.create_index("user_id")
    db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)

    db.component_definitions.create_index("type", unique=True)
    db.component_definitions.create_index("category")

    db.software.create_index("organization_id")
    db.software.create_index([("organization_id", 1), ("created_at", -1)])
    db.software.create_index("owner_id")

    db.pages.create_index("organization_id")
    db.pages.create_index("software_id")
    db.pages.create_index(
        [("software_id", 1)],
        unique=True,
        partialFilterExpression={"is_default": True},
        name="uq_one_default_per_software",
    )
    db.pages.create_index([("organization_id", 1), ("software_id", 1)])

    db.page_components.create_index("page_id")
    db.page_components.create_index("parent_id")
    db.page_components.create_index([("page_id", 1), ("order", 1)])

    db.page_data_schemas.create_index("page_id", unique=True)

    db.user_profiles.create_index("user_id", unique=True)
    db.user_profiles.create_index("organization_id")


def new_object_id() -> ObjectId:
    return ObjectId()


def utcnow() -> datetime:
    return datetime.now(UTC)


def oid(value: str) -> ObjectId:
    return ObjectId(value)


def is_valid_oid(value: str) -> bool:
    return ObjectId.is_valid(value)


def col(db: Database, name: str) -> Collection:
    return db[name]
