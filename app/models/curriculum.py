from sqlalchemy import Column, Integer, DateTime, UniqueConstraint
from datetime import datetime, timezone
from app.database import Base

class CurriculumSubject(Base):
    __tablename__ = "curriculum_subjects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    curriculum_id = Column(Integer, nullable=False, index=True)
    subject_id = Column(Integer, nullable=False, index=True)
    sequence_order = Column(Integer, nullable=False, default=1)
    prerequisite_subject_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        UniqueConstraint('curriculum_id', 'subject_id', name='uq_curriculum_subject'),
    )
