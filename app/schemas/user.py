from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CreateUserRequest(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role_id: int


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class LockUserRequest(BaseModel):
    lock_reason: str = Field(
        min_length=1,
        max_length=255
    )