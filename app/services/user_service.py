from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
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
from app.security.password import hash_password


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)

    def _to_detail_response(self, user: User) -> UserDetailResponse:
        return UserDetailResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_locked=user.is_locked,
            locked_at=user.locked_at,
            lock_reason=user.lock_reason,
            roles=user.role_names,
            permissions=user.permission_codes,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    # =========================================================================
    # S1-08: User Account Management
    # =========================================================================
    def list_users(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_locked: Optional[bool] = None,
        role: Optional[str] = None,
    ) -> UserListResponse:
        items, total = self.user_repo.get_all(
            skip=skip,
            limit=limit,
            search=search,
            is_active=is_active,
            is_locked=is_locked,
            role=role,
        )
        return UserListResponse(
            total=total,
            skip=skip,
            limit=limit,
            items=[self._to_detail_response(u) for u in items],
        )

    def get_user_by_id(self, user_id: int) -> UserDetailResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng.",
            )
        return self._to_detail_response(user)

    def create_user(self, request: UserCreateRequest) -> UserDetailResponse:
        email_clean = request.email.strip().lower()
        if self.user_repo.get_by_email(email_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã tồn tại trong hệ thống.",
            )

        roles = []
        if request.roles:
            roles = self.role_repo.get_by_names(request.roles)
            if len(roles) != len(request.roles):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Một hoặc nhiều vai trò được chọn không tồn tại.",
                )
        else:
            default_role = self.role_repo.get_by_name("TRAINEE")
            if default_role:
                roles = [default_role]

        new_user = User(
            email=email_clean,
            password_hash=hash_password(request.password),
            full_name=request.full_name,
            is_active=request.is_active,
            is_locked=False,
            roles=roles,
        )
        self.user_repo.create(new_user)
        return self._to_detail_response(new_user)

    def update_user(self, user_id: int, request: UserUpdateRequest) -> UserDetailResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng.",
            )

        if request.email is not None:
            email_clean = request.email.strip().lower()
            if email_clean != user.email:
                if self.user_repo.get_by_email(email_clean):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email đã tồn tại trong hệ thống.",
                    )
                user.email = email_clean

        if request.full_name is not None:
            user.full_name = request.full_name

        if request.is_active is not None:
            user.is_active = request.is_active
            if not user.is_active:
                # Nếu vô hiệu hóa, thu hồi toàn bộ phiên đăng nhập
                self.refresh_token_repo.revoke_all_for_user(user.id)

        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)
        return self._to_detail_response(user)

    def delete_user(self, user_id: int, current_user_id: int):
        if user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự xóa tài khoản của chính mình.",
            )

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng.",
            )

        if user.has_role("ADMIN"):
            active_admins = self.role_repo.count_active_admins()
            if active_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể xóa quản trị viên duy nhất còn lại trong hệ thống.",
                )

        self.refresh_token_repo.revoke_all_for_user(user.id)
        self.user_repo.delete(user)
        return {"message": "Xóa tài khoản người dùng thành công."}

    # =========================================================================
    # S1-09: Assign / Revoke Role
    # =========================================================================
    def assign_roles(self, user_id: int, request: AssignRolesRequest, current_user_id: int) -> RoleActionResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng.",
            )

        roles = self.role_repo.get_by_names(request.roles)
        if len(roles) != len(request.roles):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Một hoặc nhiều vai trò được chọn không tồn tại.",
            )

        # Bảo vệ: nếu người dùng đang là ADMIN và danh sách mới không có ADMIN
        if user.has_role("ADMIN") and not any(r.name == "ADMIN" for r in roles):
            active_admins = self.role_repo.count_active_admins()
            if active_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể thu hồi quyền ADMIN của quản trị viên duy nhất còn lại.",
                )

        user.roles = roles
        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)
        return RoleActionResponse(
            message="Gán vai trò thành công.",
            user_id=user.id,
            roles=user.role_names,
        )

    def revoke_role(self, user_id: int, role_name: str, current_user_id: int) -> RoleActionResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng.",
            )

        normalized_role = role_name.strip().upper()
        target_role = self.role_repo.get_by_name(normalized_role)
        if not target_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vai trò không tồn tại.",
            )

        if not user.has_role(normalized_role):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Người dùng hiện không có vai trò {normalized_role}.",
            )

        if normalized_role == "ADMIN":
            active_admins = self.role_repo.count_active_admins()
            if active_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể thu hồi quyền ADMIN của quản trị viên duy nhất còn lại.",
                )

        user.roles = [r for r in user.roles if r.name.upper() != normalized_role]
        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)
        return RoleActionResponse(
            message=f"Thu hồi vai trò {normalized_role} thành công.",
            user_id=user.id,
            roles=user.role_names,
        )

    # =========================================================================
    # S1-10: Lock / Unlock Account
    # =========================================================================
    def lock_user(self, user_id: int, request: LockUserRequest, current_user_id: int) -> LockUserResponse:
        if user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự khóa tài khoản của chính mình.",
            )

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng.",
            )

        if user.has_role("ADMIN"):
            active_admins = self.role_repo.count_active_admins()
            if active_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể khóa tài khoản của quản trị viên duy nhất còn lại.",
                )

        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản này đã bị khóa từ trước.",
            )

        user.is_locked = True
        user.locked_at = datetime.now(timezone.utc)
        user.lock_reason = request.reason or "Khóa bởi quản trị viên"
        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)

        # Thu hồi ngay lập tức mọi refresh token đang có để chấm dứt phiên làm việc
        self.refresh_token_repo.revoke_all_for_user(user.id)

        return LockUserResponse(
            message="Khóa tài khoản thành công.",
            user_id=user.id,
            is_locked=True,
            locked_at=user.locked_at,
            lock_reason=user.lock_reason,
        )

    def unlock_user(self, user_id: int) -> LockUserResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng.",
            )

        if not user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản hiện không ở trạng thái bị khóa.",
            )

        user.is_locked = False
        user.locked_at = None
        user.lock_reason = None
        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)

        return LockUserResponse(
            message="Mở khóa tài khoản thành công.",
            user_id=user.id,
            is_locked=False,
            locked_at=None,
            lock_reason=None,
        )
