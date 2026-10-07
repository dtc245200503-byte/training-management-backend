from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.role import PermissionResponse, RoleListResponse
from app.security.dependencies import get_current_user
from app.services.role_service import RoleService

router = APIRouter(prefix="/api", tags=["Roles & Permissions"])


@router.get(
    "/roles",
    response_model=RoleListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách vai trò trong hệ thống",
    description="Lấy toàn bộ các vai trò và quyền hạn tương ứng được cấu hình trong hệ thống.",
)
def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RoleService(db)
    return service.list_roles()


@router.get(
    "/permissions",
    response_model=List[PermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Danh sách quyền hạn trong hệ thống",
    description="Lấy toàn bộ danh sách các quyền hạn được hỗ trợ trong hệ thống.",
)
def list_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RoleService(db)
    return service.list_permissions()
