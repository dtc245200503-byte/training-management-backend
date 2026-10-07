from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TrainingSessionCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Mã lớp/phiên đào tạo")
    name: str = Field(..., min_length=2, max_length=255, description="Tên lớp/phiên đào tạo")
    program_id: Optional[int] = Field(None, description="ID chương trình đào tạo liên kết")
    subject_id: Optional[int] = Field(None, description="ID môn học liên kết")
    trainer_id: Optional[int] = Field(None, description="ID giảng viên phụ trách")
    start_date: datetime = Field(..., description="Thời gian bắt đầu")
    end_date: datetime = Field(..., description="Thời gian kết thúc")
    location: Optional[str] = Field(None, max_length=255, description="Địa điểm / Phòng học")
    max_trainees: int = Field(default=30, ge=1, description="Số lượng học viên tối đa")
    status: str = Field(default="SCHEDULED", description="Trạng thái (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)")


class TrainingSessionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Tên lớp/phiên đào tạo")
    program_id: Optional[int] = Field(None, description="ID chương trình đào tạo")
    subject_id: Optional[int] = Field(None, description="ID môn học")
    trainer_id: Optional[int] = Field(None, description="ID giảng viên phụ trách")
    start_date: Optional[datetime] = Field(None, description="Thời gian bắt đầu")
    end_date: Optional[datetime] = Field(None, description="Thời gian kết thúc")
    location: Optional[str] = Field(None, max_length=255, description="Địa điểm / Phòng học")
    max_trainees: Optional[int] = Field(None, ge=1, description="Số lượng học viên tối đa")
    status: Optional[str] = Field(None, description="Trạng thái")


class TrainingSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    program_id: Optional[int] = None
    program_name: Optional[str] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    trainer_id: Optional[int] = None
    trainer_name: Optional[str] = None
    start_date: datetime
    end_date: datetime
    location: Optional[str] = None
    max_trainees: int
    status: str
    created_at: datetime
    updated_at: datetime


class TrainingSessionListResponse(BaseModel):
    total: int
    items: List[TrainingSessionResponse]
