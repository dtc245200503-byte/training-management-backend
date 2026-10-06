from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.security.jwt import create_access_token, create_refresh_token
from app.security.password import verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

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

        return LoginResponse(
            message="Đăng nhập thành công",
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
