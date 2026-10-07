import re
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    session_count: int = Field(ge=1, le=1000, strict=True)
    weight: Decimal = Field(gt=0, max_digits=6, decimal_places=2)
    learning_outcomes: str | None = Field(default=None, max_length=5000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value):
        value = value.upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]*", value):
            raise ValueError("Mã môn chỉ gồm chữ không dấu, số, dấu gạch ngang hoặc gạch dưới.")
        return value

    @field_validator("learning_outcomes")
    @classmethod
    def normalize_outcomes(cls, value):
        return value or None


class SubjectProgram(BaseModel):
    curriculum_id: int
    code: str
    name: str
    is_deleted: bool


class SubjectResponse(SubjectRequest):
    subject_id: int
    class_count: int
    prerequisite_count: int
    can_delete: bool
    programs: list[SubjectProgram]


class SubjectListResponse(BaseModel):
    items: list[SubjectResponse]
    total: int
    page: int
    page_size: int


class SubjectProgramsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    curriculum_ids: list[int] = Field(max_length=1000)

    @field_validator("curriculum_ids")
    @classmethod
    def unique_ids(cls, values):
        if any(value < 1 for value in values) or len(set(values)) != len(values):
            raise ValueError("Danh sách chương trình không hợp lệ hoặc bị trùng.")
        return values
