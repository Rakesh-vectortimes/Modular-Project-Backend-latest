from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_default: bool = False
    # Reusable entity (table) this page's form reads/writes. Blank ⇒ defaults to
    # the page name, so each page gets its own table unless names are shared.
    entity_name: str | None = Field(None, max_length=255)


class PageCreate(PageBase):
    software_id: str


class PageUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    is_default: bool | None = None
    entity_name: str | None = Field(None, max_length=255)


class PageRead(PageBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    software_id: str
    created_at: datetime
    updated_at: datetime
