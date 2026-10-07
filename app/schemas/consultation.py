import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.schemas.profile import UpdateProfileRequest


class ConsultationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    full_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    email: EmailStr | None = Field(default=None, max_length=255)
    interest: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=2000)
    website: str = Field(default="", max_length=255)
    challenge_token: str = Field(min_length=32, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    challenge_answer: str = Field(min_length=1, max_length=3, pattern=r"^[0-9]+$")

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        return UpdateProfileRequest.validate_phone(value)

    @field_validator("email", "interest", "message", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value):
        if re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Họ tên không được chứa ký tự điều khiển.")
        return value


class ChallengeResponse(BaseModel):
    challenge_token: str
    question: str
    expires_in: int
    min_wait_seconds: int


class ConsultationResponse(BaseModel):
    status: Literal["new"] = "new"
    status_label: str = "Mới"
    message: str = "Cảm ơn bạn đã đăng ký tư vấn! Trung tâm đã nhận được thông tin của bạn."
    contact_promise: str = "Trung tâm sẽ liên hệ với bạn trong vòng 1 ngày làm việc."
