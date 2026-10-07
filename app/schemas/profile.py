from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255, description="Họ và tên người dùng")
    phone_number: Optional[str] = Field(None, max_length=20, description="Số điện thoại")
    bio: Optional[str] = Field(None, max_length=1000, description="Tiểu sử / Giới thiệu bản thân")
    address: Optional[str] = Field(None, max_length=255, description="Địa chỉ")
    date_of_birth: Optional[str] = Field(None, max_length=50, description="Ngày sinh (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, max_length=20, description="Giới tính")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Họ và tên không được để trống")
            return v_stripped
        return v


class UserProfileDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    is_active: bool
    is_locked: bool = False
    roles: List[str] = []
    permissions: List[str] = []
    created_at: datetime
    updated_at: datetime


class AvatarUploadResponse(BaseModel):
    message: str
    avatar_url: str
