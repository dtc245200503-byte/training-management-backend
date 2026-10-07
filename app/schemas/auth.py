from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email đăng nhập của người dùng")
    password: str = Field(..., min_length=1, description="Mật khẩu của người dùng")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_locked: bool = False


class LoginResponse(BaseModel):
    message: str = "Đăng nhập thành công"
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, description="Refresh token của người dùng")


class RefreshTokenResponse(BaseModel):
    message: str = "Làm mới token thành công"
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, description="Refresh token của phiên cần đăng xuất")


class LogoutResponse(BaseModel):
    message: str = "Đăng xuất thành công"


# S1-03: Quên và đặt lại mật khẩu
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email tài khoản cần khôi phục mật khẩu")


class ForgotPasswordResponse(BaseModel):
    message: str = "Nếu email tồn tại trong hệ thống, hướng dẫn đặt lại mật khẩu đã được gửi."


class VerifyResetTokenRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Mã đặt lại mật khẩu cần kiểm tra")


class VerifyResetTokenResponse(BaseModel):
    valid: bool
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Mã đặt lại mật khẩu")
    new_password: str = Field(..., min_length=6, description="Mật khẩu mới tối thiểu 6 ký tự")
    confirm_password: Optional[str] = Field(None, min_length=6, description="Xác nhận mật khẩu mới")


class ResetPasswordResponse(BaseModel):
    message: str = "Đặt lại mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới."


# S1-04: Đổi mật khẩu
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, description="Mật khẩu hiện tại")
    new_password: str = Field(..., min_length=6, description="Mật khẩu mới tối thiểu 6 ký tự")
    confirm_password: Optional[str] = Field(None, min_length=6, description="Xác nhận mật khẩu mới")


class ChangePasswordResponse(BaseModel):
    message: str = "Đổi mật khẩu thành công."


# S1-05: RBAC & Thông tin người dùng hiện tại
class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_locked: bool = False
    roles: List[str] = []
    permissions: List[str] = []


# S1-06: Menu theo phân quyền
class MenuItemResponse(BaseModel):
    key: str
    title: str
    path: str
    icon: Optional[str] = None
    children: List["MenuItemResponse"] = []


class MenuResponse(BaseModel):
    items: List[MenuItemResponse]


MenuItemResponse.model_rebuild()
