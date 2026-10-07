from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.consultation_lead import (
    LeadAssignRequest,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from app.security.dependencies import require_permissions
from app.services.consultation_lead_service import ConsultationLeadService

router = APIRouter(prefix="/api/leads", tags=["Consultation Leads"])


# =============================================================================
# S2-09 & S2-11: Quản lý, tìm kiếm và lọc danh sách Lead tư vấn
# =============================================================================
@router.get(
    "",
    response_model=LeadListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách yêu cầu tư vấn (Leads)",
    description="Xem danh sách khách hàng cần tư vấn với bộ lọc trạng thái, chương trình, nhân viên phụ trách và tìm kiếm.",
)
def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, description="Tìm theo tên, email, SĐT"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    program_id: Optional[int] = Query(None, description="Lọc theo ID chương trình"),
    assigned_to_id: Optional[int] = Query(None, description="Lọc theo ID nhân viên phụ trách"),
    current_user: User = Depends(require_permissions("lead:read")),
    db: Session = Depends(get_db),
):
    service = ConsultationLeadService(db)
    return service.list_leads(
        skip=skip,
        limit=limit,
        search=search,
        status_filter=status,
        program_id=program_id,
        assigned_to_id=assigned_to_id,
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết yêu cầu tư vấn",
    description="Lấy thông tin chi tiết một Lead tư vấn theo ID.",
)
def get_lead(
    lead_id: int,
    current_user: User = Depends(require_permissions("lead:read")),
    db: Session = Depends(get_db),
):
    service = ConsultationLeadService(db)
    return service.get_lead(lead_id)


@router.put(
    "/{lead_id}",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật thông tin tư vấn",
    description="Cập nhật trạng thái xử lý và ghi chú nội bộ của chuyên viên tư vấn.",
)
def update_lead(
    lead_id: int,
    request: LeadUpdate,
    current_user: User = Depends(require_permissions("lead:manage")),
    db: Session = Depends(get_db),
):
    service = ConsultationLeadService(db)
    return service.update_lead(lead_id, request)


# =============================================================================
# S2-10: Phân công tư vấn cho nhân viên (Assign Lead)
# =============================================================================
@router.post(
    "/{lead_id}/assign",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Phân công yêu cầu tư vấn",
    description="Gán nhân viên/chuyên viên phụ trách xử lý yêu cầu tư vấn của khách hàng.",
)
def assign_lead(
    lead_id: int,
    request: LeadAssignRequest,
    current_user: User = Depends(require_permissions("lead:assign")),
    db: Session = Depends(get_db),
):
    service = ConsultationLeadService(db)
    return service.assign_lead(lead_id, request)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa yêu cầu tư vấn",
    description="Xóa yêu cầu tư vấn khỏi hệ thống.",
)
def delete_lead(
    lead_id: int,
    current_user: User = Depends(require_permissions("lead:manage")),
    db: Session = Depends(get_db),
):
    service = ConsultationLeadService(db)
    return service.delete_lead(lead_id)
