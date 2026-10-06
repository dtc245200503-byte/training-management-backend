from datetime import datetime, timezone
from typing import Dict, Any
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserResponse,
)
from app.security.jwt import create_access_token, create_refresh_token, decode_token
from app.security.password import verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)

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

