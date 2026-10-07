from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from app.database import Base


class SubjectLesson(Base):
    __tablename__ = "subject_lessons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    sequence_order = Column(Integer, nullable=False)
    topic = Column(String(255), nullable=False)
    objectives = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("subject_id", "sequence_order", name="uq_subject_lesson_order"),)
