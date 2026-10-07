from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SubjectCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Mã môn học")
    name: str = Field(..., min_length=2, max_length=255, description="Tên môn học")
    description: Optional[str] = Field(None, max_length=2000, description="Mô tả môn học")
    hours: int = Field(default=0, ge=0, description="Thời lượng giờ học")
    status: str = Field(default="ACTIVE", description="Trạng thái (ACTIVE, INACTIVE)")


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Tên môn học")
    description: Optional[str] = Field(None, max_length=2000, description="Mô tả môn học")
    hours: Optional[int] = Field(None, ge=0, description="Thời lượng giờ học")
    status: Optional[str] = Field(None, description="Trạng thái (ACTIVE, INACTIVE)")


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str] = None
    hours: int
    status: str
    created_at: datetime
    updated_at: datetime


class SubjectListResponse(BaseModel):
    total: int
    items: List[SubjectResponse]
