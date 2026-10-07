from typing import List, Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.training_session import TrainingSession


class TrainingSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, session_id: int) -> Optional[TrainingSession]:
        return self.db.query(TrainingSession).filter(TrainingSession.id == session_id).first()

    def get_by_code(self, code: str) -> Optional[TrainingSession]:
        return self.db.query(TrainingSession).filter(TrainingSession.code == code.strip().upper()).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
        program_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        trainer_id: Optional[int] = None,
    ) -> Tuple[List[TrainingSession], int]:
        query = self.db.query(TrainingSession)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    TrainingSession.code.ilike(pattern),
                    TrainingSession.name.ilike(pattern),
                    TrainingSession.location.ilike(pattern),
                )
            )

        if status:
            query = query.filter(TrainingSession.status == status.strip().upper())

        if program_id:
            query = query.filter(TrainingSession.program_id == program_id)

        if subject_id:
            query = query.filter(TrainingSession.subject_id == subject_id)

        if trainer_id:
            query = query.filter(TrainingSession.trainer_id == trainer_id)

        total = query.count()
        items = query.order_by(TrainingSession.id.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, session: TrainingSession) -> TrainingSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def update(self, session: TrainingSession) -> TrainingSession:
        self.db.commit()
        self.db.refresh(session)
        return session

    def delete(self, session: TrainingSession) -> None:
        self.db.delete(session)
        self.db.commit()
