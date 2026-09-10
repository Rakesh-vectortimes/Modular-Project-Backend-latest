from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.api.deps import get_current_user
from app.db.mongo import get_db, is_valid_oid
from app.schemas.layout import PageLayoutRead, PageLayoutWrite
from app.schemas.page import PageCreate, PageRead, PageUpdate
from app.schemas.user import CurrentUser
from app.services import page_layout_service, page_service

router = APIRouter(prefix="/pages", tags=["pages"])


def _invalid_id(detail: str = "Invalid id") -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get("", response_model=list[PageRead])
def list_pages(
    software_id: str | None = None,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if software_id is not None and not is_valid_oid(software_id):
        raise _invalid_id("Invalid software_id")
    return page_service.list_pages(
        db, organization_id=current_user.organization_id, software_id=software_id
    )


@router.post("", response_model=PageRead, status_code=status.HTTP_201_CREATED)
def create_page(
    data: PageCreate,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(data.software_id):
        raise _invalid_id("Invalid software_id")
    try:
        return page_service.create_page(db, organization_id=current_user.organization_id, data=data)
    except page_service.SoftwareNotInOrganizationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{page_id}", response_model=PageRead)
def get_page(
    page_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(page_id):
        raise _invalid_id()
    page = page_service.get_page(db, page_id, current_user.organization_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.put("/{page_id}", response_model=PageRead)
def update_page(
    page_id: str,
    data: PageUpdate,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(page_id):
        raise _invalid_id()
    page = page_service.update_page(db, page_id, current_user.organization_id, data)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(
    page_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(page_id):
        raise _invalid_id()
    deleted = page_service.delete_page(db, page_id, current_user.organization_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return None


@router.patch("/{page_id}/set-default", response_model=PageRead)
def set_default_page(
    page_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(page_id):
        raise _invalid_id()
    page = page_service.set_default_page(db, page_id, current_user.organization_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.get("/{page_id}/layout", response_model=PageLayoutRead)
def get_page_layout(
    page_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(page_id):
        raise _invalid_id()
    page = page_service.get_page(db, page_id, current_user.organization_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    try:
        return page_layout_service.get_page_layout(db, page_id)
    except page_layout_service.PageLayoutNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{page_id}/layout", response_model=PageLayoutRead)
def replace_page_layout(
    page_id: str,
    data: PageLayoutWrite,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not is_valid_oid(page_id):
        raise _invalid_id()
    page = page_service.get_page(db, page_id, current_user.organization_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    try:
        return page_layout_service.replace_page_layout(
            db, page_id, data.components, settings=data.settings
        )
    except page_layout_service.PageLayoutNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except page_layout_service.InvalidLayoutError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
