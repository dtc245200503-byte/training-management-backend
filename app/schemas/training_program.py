from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.subject import SubjectResponse


class AttachSubjectRequest(BaseModel):
    subject_id: int = Field(..., description="ID môn học cần gắn vào chương trình")
    order_index: Optional[int] = Field(default=0, ge=0, description="Thứ tự môn học")
    is_mandatory: Optional[bool] = Field(default=True, description="Môn học bắt buộc hay tự chọn")


class AttachedSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    order_index: int
    is_mandatory: bool
    subject: SubjectResponse


class TrainingProgramCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Mã chương trình đào tạo")
    name: str = Field(..., min_length=2, max_length=255, description="Tên chương trình đào tạo")
    description: Optional[str] = Field(None, max_length=2000, description="Mô tả chương trình đào tạo")
    duration_hours: int = Field(default=0, ge=0, description="Tổng thời lượng giờ đào tạo")
    status: str = Field(default="ACTIVE", description="Trạng thái (ACTIVE, INACTIVE, DRAFT)")


class TrainingProgramUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Tên chương trình đào tạo")
    description: Optional[str] = Field(None, max_length=2000, description="Mô tả chương trình đào tạo")
    duration_hours: Optional[int] = Field(None, ge=0, description="Tổng thời lượng giờ đào tạo")
    status: Optional[str] = Field(None, description="Trạng thái (ACTIVE, INACTIVE, DRAFT)")


class TrainingProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str] = None
    duration_hours: int
    status: str
    created_at: datetime
    updated_at: datetime
    program_subjects: List[AttachedSubjectResponse] = []


class TrainingProgramListResponse(BaseModel):
    total: int
    items: List[TrainingProgramResponse]
