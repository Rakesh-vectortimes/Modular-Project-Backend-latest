from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.api.deps import get_current_user
from app.db.mongo import get_db, is_valid_oid
from app.schemas.layout import PublishedLayoutRead
from app.schemas.software import SoftwareCreate, SoftwareRead, SoftwareUpdate
from app.schemas.user import CurrentUser
from app.services import page_layout_service, software_service

router = APIRouter(prefix="/software", tags=["software"])


def _invalid_id(detail: str = "Invalid id") -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get("", response_model=list[SoftwareRead])
def list_software(
    skip: int = 0,
    limit: int = 100,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return software_service.list_software(
        db, organization_id=current_user.organization_id, skip=skip, limit=limit
    )


@router.post("", response_model=SoftwareRead, status_code=status.HTTP_201_CREATED)
def create_software(
    data: SoftwareCreate,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return software_service.create_software(
        db,
        organization_id=current_user.organization_id,
        owner_id=current_user.id,
        data=data,
    )


@router.get("/{software_id}", response_model=SoftwareRead)
def get_software(
    software_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(software_id):
        raise _invalid_id()
    software = software_service.get_software(db, software_id, current_user.organization_id)
    if software is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Software not found")
    return software


@router.put("/{software_id}", response_model=SoftwareRead)
def update_software(
    software_id: str,
    data: SoftwareUpdate,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(software_id):
        raise _invalid_id()
    software = software_service.update_software(
        db, software_id, current_user.organization_id, data
    )
    if software is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Software not found")
    return software


@router.delete("/{software_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_software(
    software_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(software_id):
        raise _invalid_id()
    deleted = software_service.delete_software(db, software_id, current_user.organization_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Software not found")
    return None


@router.get("/{software_id}/published", response_model=PublishedLayoutRead)
def get_published_layout(
    software_id: str,
    page_id: str | None = None,
    db: Database = Depends(get_db),
):
    """Public endpoint for the published app renderer (default or specific page)."""
    if not is_valid_oid(software_id):
        raise _invalid_id()
    if page_id is not None and not is_valid_oid(page_id):
        raise _invalid_id("Invalid page id")
    software = software_service.get_software(db, software_id)
    if software is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Software not found")

    try:
        return page_layout_service.get_published_layout(db, software_id, page_id)
    except page_layout_service.PageLayoutNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
