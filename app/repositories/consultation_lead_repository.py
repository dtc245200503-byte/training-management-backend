from typing import List, Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.consultation_lead import ConsultationLead


class ConsultationLeadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, lead_id: int) -> Optional[ConsultationLead]:
        return self.db.query(ConsultationLead).filter(ConsultationLead.id == lead_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
        program_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
    ) -> Tuple[List[ConsultationLead], int]:
        query = self.db.query(ConsultationLead)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    ConsultationLead.full_name.ilike(pattern),
                    ConsultationLead.email.ilike(pattern),
                    ConsultationLead.phone.ilike(pattern),
                )
            )

        if status:
            query = query.filter(ConsultationLead.status == status.strip().upper())

        if program_id:
            query = query.filter(ConsultationLead.program_id == program_id)

        if assigned_to_id:
            query = query.filter(ConsultationLead.assigned_to_id == assigned_to_id)

        total = query.count()
        items = query.order_by(ConsultationLead.id.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, lead: ConsultationLead) -> ConsultationLead:
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update(self, lead: ConsultationLead) -> ConsultationLead:
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def delete(self, lead: ConsultationLead) -> None:
        self.db.delete(lead)
        self.db.commit()
