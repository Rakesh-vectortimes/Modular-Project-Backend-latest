from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PositionSchema(BaseModel):
    x: float = 0
    y: float = 0
    w: float = 100
    h: float = 40
    rotation: float = 0


class LayoutNodeBase(BaseModel):
    component_type: str
    props: dict[str, Any] = Field(default_factory=dict)
    position: PositionSchema = Field(default_factory=PositionSchema)
    order: int = 0


class LayoutNodeWrite(LayoutNodeBase):
    id: str | None = None
    children: list["LayoutNodeWrite"] = Field(default_factory=list)


class LayoutNodeRead(LayoutNodeBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    children: list["LayoutNodeRead"] = Field(default_factory=list)


class PageSettings(BaseModel):
    """Figma-style page frame + published chrome."""

    backgroundColor: str = "#f4f6f9"
    backgroundImage: str = ""
    viewportWidth: int = 1280
    viewportHeight: int = 800


class PageLayoutRead(BaseModel):
    page_id: str
    components: list[LayoutNodeRead]
    settings: PageSettings = Field(default_factory=PageSettings)


class PageLayoutWrite(BaseModel):
    components: list[LayoutNodeWrite]
    settings: PageSettings | None = None


class PublishedLayoutRead(BaseModel):
    software_id: str
    page_id: str
    page_name: str
    components: list[LayoutNodeRead]
    settings: PageSettings = Field(default_factory=PageSettings)


LayoutNodeWrite.model_rebuild()
LayoutNodeRead.model_rebuild()
