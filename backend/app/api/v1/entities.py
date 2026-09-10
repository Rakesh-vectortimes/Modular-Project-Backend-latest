from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from pymongo.errors import WriteError

from app.api.deps import get_current_user
from app.db.mongo import get_db, is_valid_oid
from app.schemas.entity import (
    EntityListRead,
    EntityRead,
    RecordCreate,
    RecordListRead,
    RecordRead,
)
from app.schemas.user import CurrentUser
from app.services import entity_service

router = APIRouter(prefix="/entities", tags=["entities"])


def _invalid_id(detail: str = "Invalid id") -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get("", response_model=EntityListRead)
def list_entities(
    software_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """All reusable entities (tables) defined within one app."""
    if not is_valid_oid(software_id):
        raise _invalid_id("Invalid software_id")
    items = entity_service.list_entities(db, software_id, current_user.organization_id)
    return EntityListRead(total=len(items), items=items)


@router.get("/{entity_id}", response_model=EntityRead)
def get_entity(
    entity_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(entity_id):
        raise _invalid_id()
    entity = entity_service.get_entity(db, entity_id, current_user.organization_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity


@router.get("/{entity_id}/records", response_model=RecordListRead)
def list_records(
    entity_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Records stored in an entity — used by a Data Table bound to a table."""
    if not is_valid_oid(entity_id):
        raise _invalid_id()
    if entity_service.get_entity(db, entity_id, current_user.organization_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity_service.list_records(
        db, entity_id, skip=skip, limit=limit, organization_id=current_user.organization_id
    )


@router.post("/{entity_id}/records", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
def create_record(
    entity_id: str,
    data: RecordCreate,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(entity_id):
        raise _invalid_id()
    if entity_service.get_entity(db, entity_id, current_user.organization_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    try:
        return entity_service.insert_record(
            db, entity_id, data.values, submitted_by=current_user.id,
            organization_id=current_user.organization_id,
        )
    except entity_service.EntityHasNoDataCollectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except WriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Record did not match this entity's schema: {exc.details.get('errmsg', str(exc))}",
        ) from exc
