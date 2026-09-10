from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_default: bool = False


class PageCreate(PageBase):
    software_id: str


class PageUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    is_default: bool | None = None


class PageRead(PageBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    software_id: str
    created_at: datetime
    updated_at: datetime
