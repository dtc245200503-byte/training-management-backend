from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_
from app.models.subject import Subject
from app.models.curriculum import CurriculumSubject
from app.routers.training_programs import find_program
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.curriculum import (
    CurriculumSubjectCreate, 
    CurriculumSubjectResponse, 
    CurriculumSubjectReorder,
    CurriculumPrerequisiteUpdate,
    CurriculumReorderResponse
)
from app.crud import curriculum as crud_curriculum
from app.core.permissions import require_permission

router = APIRouter(prefix="/api/curriculums", tags=["Curriculum Management"],
                   dependencies=[Depends(require_permission("CURRICULUM_MANAGE"))])

@router.get("/{curriculum_id}/subjects", response_model=List[CurriculumSubjectResponse])
def get_subjects(curriculum_id: int, db: Session = Depends(get_db)):
    return crud_curriculum.get_curriculum_subjects(db, curriculum_id)

@router.post("/{curriculum_id}/subjects", response_model=CurriculumSubjectResponse, status_code=status.HTTP_201_CREATED)
def add_subject(curriculum_id: int, data: CurriculumSubjectCreate, db: Session = Depends(get_db)):
    return crud_curriculum.add_subject_to_curriculum(db, curriculum_id, data)

@router.delete("/{curriculum_id}/subjects/{subject_id}")
def remove_subject(curriculum_id: int, subject_id: int, db: Session = Depends(get_db)):
    return crud_curriculum.remove_subject_from_curriculum(db, curriculum_id, subject_id)

@router.put("/{curriculum_id}/subjects/reorder", response_model=CurriculumReorderResponse)
def reorder_subjects(curriculum_id: int, data: CurriculumSubjectReorder, db: Session = Depends(get_db)):
    return crud_curriculum.reorder_curriculum_subjects(db, curriculum_id, data)


@router.patch("/{curriculum_id}/subjects/{subject_id}/prerequisite", response_model=CurriculumSubjectResponse)
def update_prerequisite(curriculum_id: int, subject_id: int, data: CurriculumPrerequisiteUpdate, db: Session = Depends(get_db)):
    return crud_curriculum.update_prerequisite(db, curriculum_id, subject_id, data)


@router.get("/{curriculum_id}/available-subjects")
def available_subjects(curriculum_id: int, search: str = Query("", max_length=100), page: int = Query(1, ge=1),
                       page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    find_program(db, curriculum_id)
    existing = db.query(CurriculumSubject.subject_id).filter(CurriculumSubject.curriculum_id == curriculum_id)
    query = db.query(Subject).filter(Subject.deleted_at.is_(None), Subject.id.notin_(existing))
    if search.strip():
        value = search.strip().lower()
        query = query.filter(or_(func.lower(Subject.code).contains(value, autoescape=True), func.lower(Subject.subject_name).contains(value, autoescape=True)))
    total = query.count()
    items = query.order_by(Subject.code).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"subject_id": item.id, "code": item.code, "name": item.subject_name, "session_count": item.session_count} for item in items],
            "total": total, "page": page, "page_size": page_size}
