from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.page_data import PageDataFieldSpec


class EntityRead(BaseModel):
    """A reusable table within one app (software).

    Its `fields` manifest is auto-derived from the input components on every
    page bound to this entity (see design doc: Reusable Entities).
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    software_id: str
    name: str
    slug: str
    collection_name: str | None = None
    fields: list[PageDataFieldSpec] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EntityListRead(BaseModel):
    total: int
    items: list[EntityRead]


class RecordCreate(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class RecordRead(BaseModel):
    id: str
    entity_id: str
    values: dict[str, Any]
    submitted_at: datetime
    submitted_by: str | None = None


class RecordListRead(BaseModel):
    total: int
    items: list[RecordRead]
