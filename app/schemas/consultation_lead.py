from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PublicConsultationCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Họ và tên người cần tư vấn")
    email: EmailStr = Field(..., description="Email liên hệ")
    phone: str = Field(..., min_length=8, max_length=20, description="Số điện thoại liên hệ")
    program_id: Optional[int] = Field(None, description="ID chương trình đào tạo quan tâm")
    notes: Optional[str] = Field(None, max_length=1000, description="Nội dung cần tư vấn")
    honeypot: Optional[str] = Field(None, description="Trường chống bot tự động")


class PublicConsultationResponse(BaseModel):
    message: str
    id: int


class LeadUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Trạng thái (NEW, CONTACTED, CONSULTING, ENROLLED, REJECTED, CLOSED)")
    admin_notes: Optional[str] = Field(None, max_length=2000, description="Ghi chú nội bộ của chuyên viên tư vấn")
    notes: Optional[str] = Field(None, max_length=1000, description="Nội dung nhu cầu khách hàng")


class LeadAssignRequest(BaseModel):
    user_id: int = Field(..., description="ID nhân viên/chuyên viên phụ trách tư vấn")


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str
    program_id: Optional[int] = None
    program_name: Optional[str] = None
    notes: Optional[str] = None
    status: str
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[LeadResponse]
