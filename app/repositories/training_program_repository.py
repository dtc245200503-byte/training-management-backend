from typing import List, Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.training_program import ProgramSubject, TrainingProgram


class TrainingProgramRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, program_id: int) -> Optional[TrainingProgram]:
        return self.db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()

    def get_by_code(self, code: str) -> Optional[TrainingProgram]:
        return self.db.query(TrainingProgram).filter(TrainingProgram.code == code.strip().upper()).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[TrainingProgram], int]:
        query = self.db.query(TrainingProgram)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    TrainingProgram.code.ilike(pattern),
                    TrainingProgram.name.ilike(pattern),
                )
            )

        if status:
            query = query.filter(TrainingProgram.status == status.strip().upper())

        total = query.count()
        items = query.order_by(TrainingProgram.id.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, program: TrainingProgram) -> TrainingProgram:
        self.db.add(program)
        self.db.commit()
        self.db.refresh(program)
        return program

    def update(self, program: TrainingProgram) -> TrainingProgram:
        self.db.commit()
        self.db.refresh(program)
        return program

    def delete(self, program: TrainingProgram) -> None:
        self.db.delete(program)
        self.db.commit()

    def get_attached_subject(self, program_id: int, subject_id: int) -> Optional[ProgramSubject]:
        return (
            self.db.query(ProgramSubject)
            .filter(
                ProgramSubject.program_id == program_id,
                ProgramSubject.subject_id == subject_id,
            )
            .first()
        )

    def attach_subject(
        self,
        program_id: int,
        subject_id: int,
        order_index: int = 0,
        is_mandatory: bool = True,
    ) -> ProgramSubject:
        link = ProgramSubject(
            program_id=program_id,
            subject_id=subject_id,
            order_index=order_index,
            is_mandatory=is_mandatory,
        )
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def detach_subject(self, program_id: int, subject_id: int) -> bool:
        link = self.get_attached_subject(program_id, subject_id)
        if link:
            self.db.delete(link)
            self.db.commit()
            return True
        return False
