from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Email tài khoản người dùng")
    password: str = Field(..., min_length=6, description="Mật khẩu tối thiểu 6 ký tự")
    full_name: Optional[str] = Field(None, description="Họ và tên người dùng")
    roles: Optional[List[str]] = Field(default=["TRAINEE"], description="Danh sách tên vai trò gán cho người dùng")
    is_active: bool = Field(default=True, description="Trạng thái kích hoạt")


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, description="Họ và tên người dùng")
    email: Optional[EmailStr] = Field(None, description="Email người dùng mới (nếu thay đổi)")
    is_active: Optional[bool] = Field(None, description="Trạng thái kích hoạt tài khoản")


class UserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_locked: bool = False
    locked_at: Optional[datetime] = None
    lock_reason: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[UserDetailResponse]


class LockUserRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Lý do khóa tài khoản")


class LockUserResponse(BaseModel):
    message: str
    user_id: int
    is_locked: bool
    locked_at: Optional[datetime] = None
    lock_reason: Optional[str] = None


class AssignRolesRequest(BaseModel):
    roles: List[str] = Field(..., min_length=1, description="Danh sách tên vai trò gán cho người dùng")


class RoleActionResponse(BaseModel):
    message: str
    user_id: int
    roles: List[str]
