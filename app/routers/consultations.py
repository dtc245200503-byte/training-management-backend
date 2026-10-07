from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.consultation_lead import PublicConsultationCreate, PublicConsultationResponse
from app.services.consultation_lead_service import ConsultationLeadService

router = APIRouter(prefix="/api", tags=["Public Consultations"])


@router.post(
    "/public/consultations",
    response_model=PublicConsultationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi yêu cầu tư vấn khóa học (Public)",
    description="Endpoint công khai cho khách hàng gửi form liên hệ tư vấn đào tạo mà không cần đăng nhập.",
)
@router.post(
    "/consultations",
    response_model=PublicConsultationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def submit_consultation(
    request: PublicConsultationCreate,
    db: Session = Depends(get_db),
):
    service = ConsultationLeadService(db)
    return service.submit_public_consultation(request)
