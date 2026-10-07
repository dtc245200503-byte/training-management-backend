from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class ProgramSubject(Base):
    __tablename__ = "program_subjects"
    __table_args__ = (
        UniqueConstraint("program_id", "subject_id", name="uq_program_subject"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    program_id = Column(Integer, ForeignKey("training_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, default=0, nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    program = relationship("TrainingProgram", back_populates="program_subjects")
    subject = relationship("Subject", lazy="joined")


class TrainingProgram(Base):
    __tablename__ = "training_programs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    duration_hours = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    program_subjects = relationship(
        "ProgramSubject",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramSubject.order_index",
        lazy="joined",
    )
