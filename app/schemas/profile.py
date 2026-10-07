import re
from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    address: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value):
        if value is None or not value.strip():
            raise ValueError("Vui lòng nhập họ và tên.")
        value = value.strip()
        if len(value) > 100:
            raise ValueError("Họ và tên không được vượt quá 100 ký tự.")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not re.fullmatch(r"(?:0|\+84)(?:[35789][0-9]{8}|2[0-9]{9})", value):
            raise ValueError("Số điện thoại Việt Nam không hợp lệ. Ví dụ: 0912345678 hoặc +84912345678.")
        return "0" + value[3:] if value.startswith("+84") else value

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_date_format(cls, value):
        if value is not None and not isinstance(value, date):
            if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("Ngày sinh phải có định dạng năm-tháng-ngày.")
        return value

    @field_validator("date_of_birth")
    @classmethod
    def validate_birthday(cls, value):
        if value is not None and value > date.today():
            raise ValueError("Ngày sinh không được ở tương lai.")
        return value

    @field_validator("address")
    @classmethod
    def validate_address(cls, value):
        if value is None or not value.strip():
            return None
        value = value.strip()
        if len(value) > 255:
            raise ValueError("Địa chỉ không được vượt quá 255 ký tự.")
        return value

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Vui lòng cung cấp thông tin cần cập nhật.")
        return self


class ProfileResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    phone: str | None
    date_of_birth: date | None
    address: str | None
    avatar_url: str | None
    avatar_thumbnail_url: str | None
    roles: list[str]
    permissions: list[str]
