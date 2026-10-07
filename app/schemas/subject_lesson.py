from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class LessonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sequence_order: int = Field(ge=1, le=1000, strict=True)
    topic: str = Field(min_length=1, max_length=255)
    objectives: str = Field(min_length=1, max_length=5000)


class LessonResponse(LessonRequest):
    model_config = ConfigDict(from_attributes=True)
    lesson_id: int


class SubjectLessonsResponse(BaseModel):
    subject_id: int
    code: str
    name: str
    session_count: int
    items: list[LessonResponse]


class CloneLessonsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_subject_id: int = Field(gt=0, strict=True)
    mode: Literal["append", "replace"] = "append"
