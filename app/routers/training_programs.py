from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.database import get_db
from app.models.training_program import TrainingClass, TrainingProgram
from app.schemas.training_program import ProgramListResponse, ProgramRequest, ProgramResponse, ProgramStatusRequest


router = APIRouter(prefix="/api/curriculums", tags=["Chương trình đào tạo"],
                   dependencies=[Depends(require_permission("CURRICULUM_MANAGE"))])


def find_program(db, curriculum_id, lock=False):
    query = db.query(TrainingProgram).filter(TrainingProgram.course_id == curriculum_id,
                                           TrainingProgram.deleted_at.is_(None))
    if lock:
        query = query.with_for_update()
    program = query.first()
    if program is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy chương trình đào tạo.")
    return program


def class_counts(db, ids):
    if not ids:
        return {}
    rows = db.query(TrainingClass.course_id, TrainingClass.status, func.count(TrainingClass.class_id)).filter(
        TrainingClass.course_id.in_(ids)).group_by(TrainingClass.course_id, TrainingClass.status).all()
    result = {}
    for program_id, status, count in rows:
        total, running = result.get(program_id, (0, 0))
        result[program_id] = (total + count, running + (count if status == "in_progress" else 0))
    return result


def serialize_program(db, program, counts=None):
    counts = counts if counts is not None else class_counts(db, [program.course_id])
    total, running = counts.get(program.course_id, (0, 0))
    return {"curriculum_id": program.course_id, "code": program.code, "name": program.course_name,
            "description": program.description, "total_duration_hours": program.total_duration_hours,
            "standard_tuition": program.standard_tuition, "status": program.status,
            "active_class_count": running, "total_class_count": total, "can_delete": running == 0}


def apply_fields(program, data):
    values = data.model_dump()
    program.course_name = values.pop("name")
    for name, value in values.items():
        setattr(program, name, value)


def save_program(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mã chương trình đã tồn tại. Vui lòng chọn mã khác.")


@router.get("", response_model=ProgramListResponse)
def list_programs(search: str = Query("", max_length=100), status: Literal["active", "inactive"] | None = None,
                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(TrainingProgram).filter(TrainingProgram.deleted_at.is_(None))
    if search.strip():
        value = search.strip().lower()
        query = query.filter(or_(func.lower(TrainingProgram.code).contains(value, autoescape=True),
                                 func.lower(TrainingProgram.course_name).contains(value, autoescape=True)))
    if status:
        query = query.filter(TrainingProgram.status == status)
    total = query.count()
    items = query.order_by(TrainingProgram.course_id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    counts = class_counts(db, [item.course_id for item in items])
    return {"page": page, "page_size": page_size, "total": total,
            "items": [serialize_program(db, item, counts) for item in items]}


@router.post("", response_model=ProgramResponse, status_code=201)
def create_program(data: ProgramRequest, db: Session = Depends(get_db)):
    program = TrainingProgram()
    apply_fields(program, data)
    db.add(program)
    save_program(db)
    db.refresh(program)
    return serialize_program(db, program)


@router.get("/{curriculum_id}", response_model=ProgramResponse)
def get_program(curriculum_id: int, db: Session = Depends(get_db)):
    return serialize_program(db, find_program(db, curriculum_id))


@router.put("/{curriculum_id}", response_model=ProgramResponse)
def update_program(curriculum_id: int, data: ProgramRequest, db: Session = Depends(get_db)):
    program = find_program(db, curriculum_id, lock=True)
    apply_fields(program, data)
    save_program(db)
    db.refresh(program)
    return serialize_program(db, program)


@router.patch("/{curriculum_id}/status", response_model=ProgramResponse)
def update_program_status(curriculum_id: int, data: ProgramStatusRequest, db: Session = Depends(get_db)):
    program = find_program(db, curriculum_id, lock=True)
    program.status = data.status
    db.commit()
    db.refresh(program)
    return serialize_program(db, program)


@router.delete("/{curriculum_id}")
def delete_program(curriculum_id: int, db: Session = Depends(get_db)):
    program = find_program(db, curriculum_id, lock=True)
    running = db.query(TrainingClass).filter(TrainingClass.course_id == curriculum_id,
                                            TrainingClass.status == "in_progress").first()
    if running is not None:
        raise HTTPException(status_code=409,
                            detail="Chương trình đang có lớp chạy nên không được xóa. Bạn chỉ có thể ngừng áp dụng.")
    # Keep the referenced row to avoid the legacy FK cascading into class history.
    program.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    program.status = "inactive"
    db.commit()
    return {"message": "Đã xóa chương trình khỏi danh mục.", "curriculum_id": curriculum_id}
