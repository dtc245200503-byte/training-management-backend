from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập email và mật khẩu",
    description="Xác thực người dùng bằng email và mật khẩu, trả về thông tin xác thực JWT access token và refresh token.",
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.login(request)


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Làm mới access token",
    description="Xác thực refresh token và cấp access token mới cho phiên làm việc hiện tại.",
)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.refresh(request)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng xuất tài khoản",
    description="Thu hồi refresh token trong cơ sở dữ liệu để vô hiệu hóa phiên làm việc một cách an toàn.",
)
def logout(request: LogoutRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.logout(request)

