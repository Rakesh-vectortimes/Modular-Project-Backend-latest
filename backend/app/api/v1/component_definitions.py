from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.api.deps import require_role
from app.core.enums import UserRole
from app.db.mongo import get_db, is_valid_oid
from app.schemas.component_definition import (
    ComponentDefinitionCreate,
    ComponentDefinitionGrouped,
    ComponentDefinitionRead,
)
from app.services import component_definition_service as service

router = APIRouter(prefix="/component-definitions", tags=["component-definitions"])


@router.get("", response_model=list[ComponentDefinitionGrouped])
def list_component_definitions(db: Database = Depends(get_db)):
    definitions = service.list_component_definitions(db)
    grouped = service.group_definitions_by_category(definitions)
    return [
        ComponentDefinitionGrouped(category=category, components=items)
        for category, items in grouped.items()
    ]


@router.post("", response_model=ComponentDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_component_definition(
    data: ComponentDefinitionCreate,
    db: Database = Depends(get_db),
    _admin=Depends(require_role([UserRole.SUPER_ADMIN])),
):
    try:
        return service.create_component_definition(db, data)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Component type '{data.type}' already exists",
        ) from exc
