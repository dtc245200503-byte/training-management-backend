from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    AssignRolesRequest,
    LockUserRequest,
    LockUserResponse,
    RoleActionResponse,
    UserCreateRequest,
    UserDetailResponse,
    UserListResponse,
    UserUpdateRequest,
)
from app.security.dependencies import require_permissions
from app.services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["Users"])


# =============================================================================
# S1-08: Quản lý tài khoản người dùng
# =============================================================================
@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách tài khoản người dùng",
    description="Xem danh sách người dùng có hỗ trợ phân trang, tìm kiếm theo email/họ tên và lọc theo trạng thái, vai trò.",
)
def list_users(
    skip: int = Query(0, ge=0, description="Số bản ghi bỏ qua"),
    limit: int = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo email hoặc họ tên"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    is_locked: Optional[bool] = Query(None, description="Lọc theo trạng thái khóa"),
    role: Optional[str] = Query(None, description="Lọc theo tên vai trò"),
    current_user: User = Depends(require_permissions("user:read")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.list_users(
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active,
        is_locked=is_locked,
        role=role,
    )


@router.post(
    "",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tài khoản người dùng mới",
    description="Tạo người dùng mới với email, mật khẩu và vai trò chỉ định.",
)
def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_permissions("user:create")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.create_user(request)


@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết tài khoản người dùng",
    description="Lấy thông tin chi tiết một tài khoản kèm danh sách vai trò và quyền hạn.",
)
def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_permissions("user:read")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.get_user_by_id(user_id)


@router.put(
    "/{user_id}",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật tài khoản người dùng",
    description="Cập nhật họ tên, email hoặc trạng thái kích hoạt của người dùng.",
)
def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(require_permissions("user:update")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.update_user(user_id, request)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa tài khoản người dùng",
    description="Xóa tài khoản người dùng khỏi hệ thống. Quản trị viên không thể tự xóa tài khoản của chính mình.",
)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_permissions("user:delete")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.delete_user(user_id=user_id, current_user_id=current_user.id)


# =============================================================================
# S1-09: Gán / Thu hồi vai trò (Assign / Revoke Role)
# =============================================================================
@router.post(
    "/{user_id}/roles",
    response_model=RoleActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Gán vai trò cho người dùng",
    description="Cập nhật danh sách vai trò được cấp cho tài khoản người dùng.",
)
def assign_roles(
    user_id: int,
    request: AssignRolesRequest,
    current_user: User = Depends(require_permissions("role:assign")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.assign_roles(
        user_id=user_id,
        request=request,
        current_user_id=current_user.id,
    )


@router.delete(
    "/{user_id}/roles/{role_name}",
    response_model=RoleActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Thu hồi một vai trò của người dùng",
    description="Gỡ bỏ một vai trò cụ thể khỏi tài khoản người dùng.",
)
def revoke_role(
    user_id: int,
    role_name: str,
    current_user: User = Depends(require_permissions("role:assign")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.revoke_role(
        user_id=user_id,
        role_name=role_name,
        current_user_id=current_user.id,
    )


# =============================================================================
# S1-10: Khóa / Mở khóa tài khoản (Lock / Unlock Account)
# =============================================================================
@router.post(
    "/{user_id}/lock",
    response_model=LockUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Khóa tài khoản người dùng",
    description="Khóa tài khoản kèm lý do và lập tức thu hồi mọi phiên đăng nhập của người dùng này.",
)
def lock_user(
    user_id: int,
    request: LockUserRequest,
    current_user: User = Depends(require_permissions("user:lock")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.lock_user(
        user_id=user_id,
        request=request,
        current_user_id=current_user.id,
    )


@router.post(
    "/{user_id}/unlock",
    response_model=LockUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Mở khóa tài khoản người dùng",
    description="Mở khóa tài khoản cho phép người dùng tiếp tục đăng nhập và sử dụng hệ thống.",
)
def unlock_user(
    user_id: int,
    current_user: User = Depends(require_permissions("user:lock")),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.unlock_user(user_id=user_id)
