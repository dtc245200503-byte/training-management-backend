from datetime import datetime, timezone
import re
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.consultation_lead import ConsultationLead
from app.repositories.consultation_lead_repository import ConsultationLeadRepository
from app.repositories.training_program_repository import TrainingProgramRepository
from app.repositories.user_repository import UserRepository
from app.schemas.consultation_lead import (
    LeadAssignRequest,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
    PublicConsultationCreate,
    PublicConsultationResponse,
)

PHONE_REGEX = re.compile(r"^[0-9+\-\s()]{8,20}$")


class ConsultationLeadService:
    def __init__(self, db: Session):
        self.db = db
        self.lead_repo = ConsultationLeadRepository(db)
        self.program_repo = TrainingProgramRepository(db)
        self.user_repo = UserRepository(db)

    def _to_lead_response(self, lead: ConsultationLead) -> LeadResponse:
        return LeadResponse(
            id=lead.id,
            full_name=lead.full_name,
            email=lead.email,
            phone=lead.phone,
            program_id=lead.program_id,
            program_name=lead.program.name if lead.program else None,
            notes=lead.notes,
            status=lead.status,
            assigned_to_id=lead.assigned_to_id,
            assigned_to_name=lead.assigned_to.full_name if lead.assigned_to else None,
            assigned_at=lead.assigned_at,
            admin_notes=lead.admin_notes,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )

    # =========================================================================
    # S2-08: Public Consultation Submission
    # =========================================================================
    def submit_public_consultation(self, request: PublicConsultationCreate) -> PublicConsultationResponse:
        # Cơ chế chống bot spam: Honeypot trap
        if request.honeypot and request.honeypot.strip():
            # Trả về thành công giả lập để đánh lừa bot mà không lưu vào hệ thống
            return PublicConsultationResponse(
                message="Gửi yêu cầu tư vấn thành công. Chúng tôi sẽ liên hệ với bạn sớm nhất.",
                id=0,
            )

        phone_clean = request.phone.strip()
        if not PHONE_REGEX.match(phone_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Số điện thoại không đúng định dạng.",
            )

        if request.program_id is not None:
            program = self.program_repo.get_by_id(request.program_id)
            if not program:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chương trình đào tạo quan tâm không tồn tại.",
                )

        lead = ConsultationLead(
            full_name=request.full_name.strip(),
            email=request.email.strip().lower(),
            phone=phone_clean,
            program_id=request.program_id,
            notes=request.notes.strip() if request.notes else None,
            status="NEW",
        )
        self.lead_repo.create(lead)

        return PublicConsultationResponse(
            message="Gửi yêu cầu tư vấn thành công. Chúng tôi sẽ liên hệ với bạn sớm nhất.",
            id=lead.id,
        )

    # =========================================================================
    # S2-09 & S2-11: Lead Management, Search and Filter
    # =========================================================================
    def list_leads(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        program_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
    ) -> LeadListResponse:
        items, total = self.lead_repo.get_all(
            skip=skip,
            limit=limit,
            search=search,
            status=status_filter,
            program_id=program_id,
            assigned_to_id=assigned_to_id,
        )
        return LeadListResponse(
            total=total,
            skip=skip,
            limit=limit,
            items=[self._to_lead_response(l) for l in items],
        )

    def get_lead(self, lead_id: int) -> LeadResponse:
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy yêu cầu tư vấn.",
            )
        return self._to_lead_response(lead)

    def update_lead(self, lead_id: int, request: LeadUpdate) -> LeadResponse:
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy yêu cầu tư vấn.",
            )

        valid_statuses = {"NEW", "CONTACTED", "CONSULTING", "ENROLLED", "REJECTED", "CLOSED"}
        if request.status is not None:
            norm_status = request.status.strip().upper()
            if norm_status not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Trạng thái '{request.status}' không hợp lệ. Các trạng thái được phép: {', '.join(sorted(valid_statuses))}",
                )
            lead.status = norm_status

        if request.admin_notes is not None:
            lead.admin_notes = request.admin_notes.strip()
        if request.notes is not None:
            lead.notes = request.notes.strip()

        lead.updated_at = datetime.now(timezone.utc)
        self.lead_repo.update(lead)
        return self._to_lead_response(lead)

    # =========================================================================
    # S2-10: Assign Lead
    # =========================================================================
    def assign_lead(self, lead_id: int, request: LeadAssignRequest) -> LeadResponse:
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy yêu cầu tư vấn.",
            )

        assignee = self.user_repo.get_by_id(request.user_id)
        if not assignee or not assignee.is_active or assignee.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Người được phân công không tồn tại hoặc tài khoản đang bị khóa/vô hiệu hóa.",
            )

        lead.assigned_to_id = assignee.id
        lead.assigned_at = datetime.now(timezone.utc)
        if lead.status == "NEW":
            lead.status = "CONTACTED"

        lead.updated_at = datetime.now(timezone.utc)
        self.lead_repo.update(lead)
        return self._to_lead_response(lead)

    def delete_lead(self, lead_id: int) -> dict:
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy yêu cầu tư vấn.",
            )
        self.lead_repo.delete(lead)
        return {"message": "Xóa yêu cầu tư vấn thành công."}
