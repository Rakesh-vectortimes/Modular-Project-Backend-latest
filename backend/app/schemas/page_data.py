from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PageDataFieldSpec(BaseModel):
    key: str
    label: str
    component_type: str
    data_type: str = "string"  # string | number | boolean | array
    required: bool = False
    unique: bool = False


class PageDataSchemaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_id: str
    collection_name: str | None = None
    fields: list[PageDataFieldSpec] = Field(default_factory=list)
    # The reusable entity (table) this page's form is bound to.
    entity_id: str | None = None
    entity_name: str | None = None
    updated_at: datetime | None = None


class SubmissionCreate(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class SubmissionRead(BaseModel):
    id: str
    page_id: str
    values: dict[str, Any]
    submitted_at: datetime
    submitted_by: str | None = None


class SubmissionListRead(BaseModel):
    total: int
    items: list[SubmissionRead]
