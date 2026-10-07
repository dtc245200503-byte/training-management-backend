from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.permissions import require_permission
from app.database import get_db
from app.crud.subjects import find_subject
from app.crud.subject_lessons import clone_lessons, lessons_query, save_lesson, serialize_lessons
from app.models.subject_lesson import SubjectLesson
from app.schemas.subject_lesson import CloneLessonsRequest, LessonRequest, LessonResponse, SubjectLessonsResponse

router = APIRouter(prefix="/api/subjects", tags=["Buổi học trong môn"],
                   dependencies=[Depends(require_permission("SUBJECT_MANAGE"))])


@router.get("/{subject_id}/lessons", response_model=SubjectLessonsResponse)
def list_lessons(subject_id: int, db: Session = Depends(get_db)):
    return serialize_lessons(db, find_subject(db, subject_id))


@router.post("/{subject_id}/lessons", response_model=LessonResponse, status_code=201)
def create_lesson(subject_id: int, data: LessonRequest, db: Session = Depends(get_db)):
    return save_lesson(db, subject_id, data)


@router.put("/{subject_id}/lessons/{lesson_id}", response_model=LessonResponse)
def update_lesson(subject_id: int, lesson_id: int, data: LessonRequest, db: Session = Depends(get_db)):
    return save_lesson(db, subject_id, data, lesson_id)


@router.delete("/{subject_id}/lessons/{lesson_id}")
def delete_lesson(subject_id: int, lesson_id: int, db: Session = Depends(get_db)):
    find_subject(db, subject_id, lock=True)
    lesson = lessons_query(db, subject_id).filter(SubjectLesson.id == lesson_id).first()
    if lesson is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi học trong môn này.")
    db.delete(lesson); db.commit()
    return {"message": "Đã gỡ buổi học khỏi môn."}


@router.post("/{subject_id}/lessons/clone", response_model=SubjectLessonsResponse)
def copy_lessons(subject_id: int, data: CloneLessonsRequest, db: Session = Depends(get_db)):
    return clone_lessons(db, subject_id, data)
