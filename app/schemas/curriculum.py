from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# Schema khi thêm môn học vào chương trình
class CurriculumSubjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: int = Field(gt=0, strict=True)
    subject_name: Optional[str] = None  # <--- BỔ SUNG DÒNG NÀY
    sequence_order: Optional[int] = Field(default=None, gt=0, strict=True)
    prerequisite_subject_id: Optional[int] = Field(default=None, gt=0, strict=True)


class CurriculumPrerequisiteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prerequisite_subject_id: Optional[int] = Field(..., gt=0, strict=True)

# Schema cập nhật thứ tự (dùng cho Drag-and-drop)
class SubjectOrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: int = Field(gt=0, strict=True)
    sequence_order: int = Field(gt=0, strict=True)

class CurriculumSubjectReorder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: List[SubjectOrderItem] = Field(max_length=1000)

# Schema trả về kết quả
class CurriculumSubjectResponse(BaseModel):
    id: int
    curriculum_id: int
    subject_id: int
    subject_name: Optional[str] = None
    sequence_order: int
    prerequisite_subject_id: Optional[int] = None
    prerequisite_subject_name: Optional[str] = None
    created_at: datetime | None
    subject_code: str
    session_count: int
    weight: Decimal
    learning_outcomes: str | None

    model_config = ConfigDict(from_attributes=True)


class CurriculumReorderResponse(BaseModel):
    message: str
    items: List[CurriculumSubjectResponse]
