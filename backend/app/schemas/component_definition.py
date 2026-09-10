from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PropertySchemaField(BaseModel):
    key: str
    label: str
    inputType: str
    options: list[str] | None = None


class ComponentDefinitionBase(BaseModel):
    type: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=255)
    icon: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    default_props: dict[str, Any] = Field(default_factory=dict)
    property_schema: list[PropertySchemaField] = Field(default_factory=list)
    is_container: bool = False
    # True for components that capture user input (text/email/password/date/etc.).
    # Drives the auto-created per-page MongoDB collection (see page_data_schema_service).
    is_input: bool = False
    # Optional Mongo field type used when this component is_input (string/number/boolean/array).
    data_type: str = "string"


class ComponentDefinitionCreate(ComponentDefinitionBase):
    pass


class ComponentDefinitionRead(ComponentDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ComponentDefinitionGrouped(BaseModel):
    category: str
    components: list[ComponentDefinitionRead]
