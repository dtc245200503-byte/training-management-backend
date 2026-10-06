from typing import Optional
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


class LoginResponse(BaseModel):
    message: str = "Đăng nhập thành công"
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
