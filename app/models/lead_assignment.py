from sqlalchemy import Column, ForeignKey, Integer, String, Text
from app.database import Base
from app.models.consultation import PRECISE_DATETIME


class LeadAssignmentHistory(Base):
    __tablename__ = "lead_assignment_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("consultation_leads.lead_id"), nullable=False, index=True)
    from_assignee_id = Column(Integer, nullable=True)
    to_assignee_id = Column(Integer, nullable=True)
    actor_id = Column(Integer, nullable=False)
    # Snapshots retain the meaning of a transfer when accounts are renamed.
    from_assignee_name = Column(String(100), nullable=True)
    to_assignee_name = Column(String(100), nullable=True)
    actor_name = Column(String(100), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(PRECISE_DATETIME, nullable=False)
