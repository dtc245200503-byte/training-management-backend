from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any, Dict, List, Optional
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    MenuItemResponse,
    MenuResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserResponse,
    VerifyResetTokenRequest,
    VerifyResetTokenResponse,
)
from app.security.jwt import create_access_token, create_refresh_token, decode_token
from app.security.password import hash_password, verify_password
from app.services.email_service import EmailService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)
        self.reset_repo = PasswordResetRepository(db)

    def login(self, request: LoginRequest) -> LoginResponse:
        user = self.user_repo.get_by_email(request.email)

        # Chống account enumeration: trả cùng thông báo lỗi khi email sai hoặc mật khẩu sai
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản đã bị vô hiệu hóa.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # S1-10: Tài khoản bị khóa không được phép đăng nhập
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_payload = {
            "sub": str(user.id),
            "email": user.email,
        }

        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)

        # Lưu refresh token vào database (session persistence)
        payload = decode_token(refresh_token)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        self.refresh_token_repo.create(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
        )

        return LoginResponse(
            message="Đăng nhập thành công",
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    def _validate_refresh_token(self, token_str: str) -> RefreshToken:
        token = token_str.strip()

        # 1. Giải mã và xác thực chữ ký JWT
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token đã hết hạn.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 2. Kiểm tra loại token phải là refresh
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Kiểm tra token có trong database không (phiên đăng nhập tồn tại)
        db_token = self.refresh_token_repo.get_by_token(token)
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 4. Kiểm tra token đã bị thu hồi chưa
        if db_token.is_revoked or db_token.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token đã bị thu hồi.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 5. Kiểm tra thời hạn lưu trong database
        now = datetime.now(timezone.utc)
        expires_at = db_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token đã hết hạn.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return db_token

    def refresh(self, request: RefreshTokenRequest) -> RefreshTokenResponse:
        db_token = self._validate_refresh_token(request.refresh_token)

        # Kiểm tra trạng thái tài khoản người dùng
        user = self.user_repo.get_by_id(db_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản không tồn tại hoặc đã bị vô hiệu hóa.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # S1-10: Kiểm tra tài khoản có bị khóa không
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản của bạn đã bị khóa.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Cấp access token mới
        token_payload = {
            "sub": str(user.id),
            "email": user.email,
        }
        new_access_token = create_access_token(token_payload)

        return RefreshTokenResponse(
            message="Làm mới token thành công",
            access_token=new_access_token,
            refresh_token=request.refresh_token,
            token_type="bearer",
        )

    def logout(self, request: LogoutRequest) -> LogoutResponse:
        db_token = self._validate_refresh_token(request.refresh_token)

        # Thu hồi refresh token trong database
        self.refresh_token_repo.revoke(db_token)

        return LogoutResponse(
            message="Đăng xuất thành công"
        )

    # =========================================================================
    # S1-03: Forgot / Reset Password
    # =========================================================================
    def forgot_password(self, request: ForgotPasswordRequest) -> ForgotPasswordResponse:
        user = self.user_repo.get_by_email(request.email)

        # Nếu user tồn tại, đang hoạt động và không bị khóa -> tạo reset token
        if user and user.is_active and not user.is_locked:
            # Tạo raw token ngẫu nhiên bảo mật cao
            raw_token = secrets.token_urlsafe(32)
            # Hash SHA-256 để lưu DB (tuyệt đối không lưu raw token dạng plain-text)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

            # Vô hiệu hóa các mã reset trước đó của user
            self.reset_repo.invalidate_all_for_user(user.id)

            # Token hết hạn sau 15 phút
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            self.reset_repo.create(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )

            # Gửi email giả lập chứa mã đặt lại mật khẩu
            EmailService.send_password_reset_email(user.email, raw_token)

        # Trả thông báo đồng nhất để chống account enumeration
        return ForgotPasswordResponse(
            message="Nếu email tồn tại trong hệ thống, hướng dẫn đặt lại mật khẩu đã được gửi."
        )

    def _get_valid_reset_token(self, token_str: str):
        token_clean = token_str.strip()
        token_hash = hashlib.sha256(token_clean.encode("utf-8")).hexdigest()
        db_token = self.reset_repo.get_by_token_hash(token_hash)

        if not db_token or db_token.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
            )

        now = datetime.now(timezone.utc)
        expires_at = db_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
            )

        return db_token

    def verify_reset_token(self, request: VerifyResetTokenRequest) -> VerifyResetTokenResponse:
        self._get_valid_reset_token(request.token)
        return VerifyResetTokenResponse(
            valid=True,
            message="Mã xác thực hợp lệ.",
        )

    def reset_password(self, request: ResetPasswordRequest) -> ResetPasswordResponse:
        if request.confirm_password is not None and request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu xác nhận không khớp.",
            )

        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu mới phải có ít nhất 6 ký tự.",
            )

        db_token = self._get_valid_reset_token(request.token)
        user = self.user_repo.get_by_id(db_token.user_id)
        if not user or not user.is_active or user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản không hợp lệ hoặc đã bị khóa.",
            )

        # Cập nhật mật khẩu mới đã mã hóa bcrypt
        user.password_hash = hash_password(request.new_password)
        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)

        # Đánh dấu token đã sử dụng
        self.reset_repo.mark_used(db_token)

        # Hủy toàn bộ refresh token cũ để buộc đăng nhập lại
        self.refresh_token_repo.revoke_all_for_user(user.id)

        return ResetPasswordResponse(
            message="Đặt lại mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới."
        )

    # =========================================================================
    # S1-04: Change Password
    # =========================================================================
    def change_password(self, user: User, request: ChangePasswordRequest) -> ChangePasswordResponse:
        if not verify_password(request.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu hiện tại không chính xác.",
            )

        if request.confirm_password is not None and request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu xác nhận không khớp.",
            )

        if request.new_password == request.old_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu mới không được trùng với mật khẩu cũ.",
            )

        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu mới phải có ít nhất 6 ký tự.",
            )

        # Cập nhật mật khẩu mới
        user.password_hash = hash_password(request.new_password)
        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)

        # Thu hồi tất cả các phiên đăng nhập khác của user để đảm bảo an toàn
        self.refresh_token_repo.revoke_all_for_user(user.id)

        return ChangePasswordResponse(message="Đổi mật khẩu thành công.")

    # =========================================================================
    # S1-06: Menu by Permission
    # =========================================================================
    def get_menu_for_user(self, user: User) -> MenuResponse:
        """Trả về cấu trúc menu theo vai trò và quyền hạn của người dùng."""
        all_menu_configs = [
            {
                "key": "dashboard",
                "title": "Trang chủ",
                "path": "/dashboard",
                "icon": "dashboard",
                "permission": None,
                "roles": None,
                "children": [],
            },
            {
                "key": "users",
                "title": "Quản lý người dùng",
                "path": "/users",
                "icon": "users",
                "permission": "user:read",
                "roles": ["ADMIN"],
                "children": [
                    {
                        "key": "users-list",
                        "title": "Danh sách người dùng",
                        "path": "/users",
                        "icon": "user-list",
                        "permission": "user:read",
                        "roles": ["ADMIN"],
                        "children": [],
                    },
                    {
                        "key": "roles-manage",
                        "title": "Phân quyền vai trò",
                        "path": "/roles",
                        "icon": "shield-check",
                        "permission": "role:assign",
                        "roles": ["ADMIN"],
                        "children": [],
                    },
                ],
            },
            {
                "key": "courses",
                "title": "Quản lý khóa học",
                "path": "/courses",
                "icon": "book",
                "permission": "course:manage",
                "roles": ["ADMIN", "TRAINER"],
                "children": [],
            },
            {
                "key": "my-courses",
                "title": "Khóa học của tôi",
                "path": "/my-courses",
                "icon": "academic-cap",
                "permission": "course:read",
                "roles": None,
                "children": [],
            },
            {
                "key": "reports",
                "title": "Báo cáo thống kê",
                "path": "/reports",
                "icon": "chart",
                "permission": "report:view",
                "roles": ["ADMIN", "TRAINER"],
                "children": [],
            },
            {
                "key": "settings",
                "title": "Cài đặt hệ thống",
                "path": "/settings",
                "icon": "cog",
                "permission": None,
                "roles": ["ADMIN"],
                "children": [],
            },
        ]

        def can_access(item: dict) -> bool:
            if user.has_role("ADMIN"):
                return True
            # Kiểm tra role nếu có
            if item.get("roles") is not None:
                if not any(user.has_role(r) for r in item["roles"]):
                    return False
            # Kiểm tra permission nếu có
            if item.get("permission") is not None:
                if not user.has_permission(item["permission"]):
                    return False
            return True

        visible_items: List[MenuItemResponse] = []
        for parent in all_menu_configs:
            if not can_access(parent):
                continue

            children_items: List[MenuItemResponse] = []
            if parent.get("children"):
                for child in parent["children"]:
                    if can_access(child):
                        children_items.append(
                            MenuItemResponse(
                                key=child["key"],
                                title=child["title"],
                                path=child["path"],
                                icon=child.get("icon"),
                                children=[],
                            )
                        )

            visible_items.append(
                MenuItemResponse(
                    key=parent["key"],
                    title=parent["title"],
                    path=parent["path"],
                    icon=parent.get("icon"),
                    children=children_items,
                )
            )

        return MenuResponse(items=visible_items)
