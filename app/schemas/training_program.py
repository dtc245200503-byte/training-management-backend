import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProgramStatus = Literal["active", "inactive"]


class ProgramRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    total_duration_hours: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    standard_tuition: Decimal = Field(ge=0, max_digits=12, decimal_places=0)
    status: ProgramStatus = "active"

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value):
        value = value.upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]*", value):
            raise ValueError("Mã chương trình chỉ gồm chữ không dấu, số, dấu gạch ngang hoặc gạch dưới.")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value):
        return value or None


class ProgramStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ProgramStatus


class ProgramResponse(BaseModel):
    curriculum_id: int
    code: str
    name: str
    description: str | None
    total_duration_hours: Decimal
    standard_tuition: Decimal
    status: ProgramStatus
    active_class_count: int
    total_class_count: int
    can_delete: bool


class ProgramListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[ProgramResponse]
