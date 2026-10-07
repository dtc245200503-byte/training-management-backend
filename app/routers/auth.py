from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    MenuResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserProfileResponse,
    VerifyResetTokenRequest,
    VerifyResetTokenResponse,
)
from app.security.dependencies import get_current_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# =============================================================================
# S1-01 & S1-02: Authentication & Session
# =============================================================================
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


# =============================================================================
# S1-03: Forgot & Reset Password
# =============================================================================
@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Yêu cầu đặt lại mật khẩu",
    description="Gửi mã/link đặt lại mật khẩu đến email người dùng nếu tài khoản tồn tại trong hệ thống.",
)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.forgot_password(request)


@router.post(
    "/verify-reset-token",
    response_model=VerifyResetTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Kiểm tra mã đặt lại mật khẩu",
    description="Xác minh mã đặt lại mật khẩu có hợp lệ và còn thời hạn hay không.",
)
def verify_reset_token(request: VerifyResetTokenRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.verify_reset_token(request)


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Đặt lại mật khẩu mới",
    description="Thiết lập mật khẩu mới bằng mã đặt lại mật khẩu hợp lệ và hủy các phiên làm việc cũ.",
)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.reset_password(request)


# =============================================================================
# S1-04: Change Password
# =============================================================================
@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Đổi mật khẩu người dùng",
    description="Người dùng đã đăng nhập tự đổi mật khẩu bằng cách xác thực mật khẩu hiện tại.",
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    return service.change_password(current_user, request)


# =============================================================================
# S1-05: Current User Profile (RBAC & Thông tin cá nhân)
# =============================================================================
@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin tài khoản hiện tại",
    description="Trả về thông tin người dùng đang đăng nhập kèm danh sách vai trò và quyền hạn.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_locked=current_user.is_locked,
        roles=current_user.role_names,
        permissions=current_user.permission_codes,
    )


# =============================================================================
# S1-06: Menu by Permission
# =============================================================================
@router.get(
    "/menu",
    response_model=MenuResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy cấu trúc menu theo phân quyền",
    description="Trả về danh sách menu được phép truy cập dựa trên vai trò và quyền hạn của người dùng đăng nhập.",
)
def get_menu(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    return service.get_menu_for_user(current_user)
