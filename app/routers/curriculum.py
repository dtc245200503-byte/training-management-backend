from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.curriculum import (
    CurriculumSubjectCreate, 
    CurriculumSubjectResponse, 
    CurriculumSubjectReorder
)
from app.crud import curriculum as crud_curriculum

router = APIRouter(prefix="/api/curriculums", tags=["Curriculum Management"])

@router.get("/{curriculum_id}/subjects", response_model=List[CurriculumSubjectResponse])
def get_subjects(curriculum_id: int, db: Session = Depends(get_db)):
    return crud_curriculum.get_curriculum_subjects(db, curriculum_id)

@router.post("/{curriculum_id}/subjects", response_model=CurriculumSubjectResponse, status_code=status.HTTP_201_CREATED)
def add_subject(curriculum_id: int, data: CurriculumSubjectCreate, db: Session = Depends(get_db)):
    return crud_curriculum.add_subject_to_curriculum(db, curriculum_id, data)

@router.delete("/{curriculum_id}/subjects/{subject_id}")
def remove_subject(curriculum_id: int, subject_id: int, db: Session = Depends(get_db)):
    return crud_curriculum.remove_subject_from_curriculum(db, curriculum_id, subject_id)

@router.put("/{curriculum_id}/subjects/reorder")
def reorder_subjects(curriculum_id: int, data: CurriculumSubjectReorder, db: Session = Depends(get_db)):
    return crud_curriculum.reorder_curriculum_subjects(db, curriculum_id, data)