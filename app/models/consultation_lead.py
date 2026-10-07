from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class ConsultationLead(Base):
    __tablename__ = "consultation_leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    program_id = Column(Integer, ForeignKey("training_programs.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = Column(String(1000), nullable=True)
    status = Column(String(20), default="NEW", nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    admin_notes = Column(String(2000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    program = relationship("TrainingProgram", lazy="joined")
    assigned_to = relationship("User", lazy="joined")
