from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from pymongo.errors import WriteError

from app.api.deps import get_current_user
from app.db.mongo import get_db, is_valid_oid
from app.schemas.page_data import (
    PageDataSchemaRead,
    SubmissionCreate,
    SubmissionListRead,
    SubmissionRead,
)
from app.schemas.user import CurrentUser
from app.services import entity_service, page_service

router = APIRouter(prefix="/pages", tags=["page-data"])


def _invalid_id(detail: str = "Invalid id") -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get("/{page_id}/data-schema", response_model=PageDataSchemaRead)
def get_data_schema(
    page_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """The auto-derived field manifest for this page's form (see design doc §6)."""
    if not is_valid_oid(page_id):
        raise _invalid_id()
    page = page_service.get_page(db, page_id, current_user.organization_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return entity_service.get_schema_for_page(db, page_id)


@router.post("/{page_id}/submissions", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def create_submission(
    page_id: str,
    data: SubmissionCreate,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Called by a Button's `submit` action in Run mode."""
    if not is_valid_oid(page_id):
        raise _invalid_id()
    page = page_service.get_page(db, page_id, current_user.organization_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    try:
        record = entity_service.insert_record_for_page(
            db, page_id, data.values, submitted_by=current_user.id
        )
        return SubmissionRead(
            id=record.id,
            page_id=page_id,
            values=record.values,
            submitted_at=record.submitted_at,
            submitted_by=record.submitted_by,
        )
    except entity_service.PageHasNoDataCollectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except WriteError as exc:
        # The $jsonSchema validator rejected this document — e.g. a required
        # field (like a unique email) was missing or the wrong type.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Submission did not match this page's data schema: {exc.details.get('errmsg', str(exc))}",
        ) from exc


@router.get("/{page_id}/submissions", response_model=SubmissionListRead)
def list_submissions(
    page_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Used by the Data Table component to show another page's captured data."""
    if not is_valid_oid(page_id):
        raise _invalid_id()
    page = page_service.get_page(db, page_id, current_user.organization_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    records = entity_service.list_records_for_page(db, page_id, skip=skip, limit=limit)
    return SubmissionListRead(
        total=records.total,
        items=[
            SubmissionRead(
                id=r.id,
                page_id=page_id,
                values=r.values,
                submitted_at=r.submitted_at,
                submitted_by=r.submitted_by,
            )
            for r in records.items
        ],
    )
