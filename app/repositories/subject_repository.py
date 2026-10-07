from typing import List, Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.subject import Subject


class SubjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, subject_id: int) -> Optional[Subject]:
        return self.db.query(Subject).filter(Subject.id == subject_id).first()

    def get_by_code(self, code: str) -> Optional[Subject]:
        return self.db.query(Subject).filter(Subject.code == code.strip().upper()).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Subject], int]:
        query = self.db.query(Subject)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Subject.code.ilike(pattern),
                    Subject.name.ilike(pattern),
                )
            )

        if status:
            query = query.filter(Subject.status == status.strip().upper())

        total = query.count()
        items = query.order_by(Subject.id.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, subject: Subject) -> Subject:
        self.db.add(subject)
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def update(self, subject: Subject) -> Subject:
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def delete(self, subject: Subject) -> None:
        self.db.delete(subject)
        self.db.commit()
