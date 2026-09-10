from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.api.deps import get_current_user, require_role
from app.core.enums import UserRole, UserStatus
from app.db.mongo import get_db, is_valid_oid
from app.schemas.user import CurrentUser, UserCreate, UserListResponse, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


def _invalid_id() -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id")


@router.get("", response_model=UserListResponse)
def list_users(
    search: str | None = Query(None, description="Search by name, email, or mobile"),
    role: UserRole | None = None,
    status: UserStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    return user_service.list_users(
        db,
        organization_id=current_user.organization_id,
        search=search,
        role=role,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    try:
        return user_service.create_user(
            db,
            organization_id=current_user.organization_id,
            data=data,
            actor_role=current_user.role,
        )
    except user_service.EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except user_service.RolePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    if not is_valid_oid(user_id):
        raise _invalid_id()
    user = user_service.get_user_in_organization(db, user_id, current_user.organization_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    data: UserUpdate,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    if not is_valid_oid(user_id):
        raise _invalid_id()
    try:
        user = user_service.update_user(
            db,
            user_id=user_id,
            organization_id=current_user.organization_id,
            data=data,
            actor_role=current_user.role,
        )
    except user_service.EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except user_service.RolePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Database = Depends(get_db),
    current_user: CurrentUser = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    if not is_valid_oid(user_id):
        raise _invalid_id()
    try:
        deleted = user_service.delete_user(
            db,
            user_id=user_id,
            organization_id=current_user.organization_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
        )
    except user_service.RolePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not deleted:
        if user_id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None
