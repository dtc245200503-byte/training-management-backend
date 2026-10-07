from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.permissions import require_permission
from app.database import get_db
from app.models.subject import Subject
from app.models.curriculum import CurriculumSubject
from app.models.training_program import TrainingProgram
from app.crud.subjects import capture_class_usage, class_usage_query, find_subject, serialize_subjects
from app.schemas.subject import SubjectListResponse, SubjectProgramsRequest, SubjectRequest, SubjectResponse
from app.crud.curriculum import normalize_program_order
from app.crud.subject_lessons import check_subject_capacity

router = APIRouter(prefix="/api/subjects", tags=["Danh mục môn học"],
                   dependencies=[Depends(require_permission("SUBJECT_MANAGE"))])


def commit_subject(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mã môn học đã tồn tại. Vui lòng chọn mã khác.")


def apply_fields(subject, data):
    subject.code = data.code
    subject.subject_name = data.name
    subject.session_count = data.session_count
    subject.weight = data.weight
    subject.description = data.learning_outcomes


@router.get("", response_model=SubjectListResponse)
def list_subjects(search: str = Query("", max_length=100), page: int = Query(1, ge=1),
                  page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(Subject).filter(Subject.deleted_at.is_(None))
    if search.strip():
        value = search.strip().lower()
        query = query.filter(or_(func.lower(Subject.code).contains(value, autoescape=True),
                                 func.lower(Subject.subject_name).contains(value, autoescape=True)))
    total = query.count()
    subjects = query.order_by(Subject.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": serialize_subjects(db, subjects), "total": total, "page": page, "page_size": page_size}


@router.get("/program-options", dependencies=[Depends(require_permission("CURRICULUM_MANAGE"))])
def program_options(db: Session = Depends(get_db)):
    programs = db.query(TrainingProgram).filter(TrainingProgram.deleted_at.is_(None)).order_by(TrainingProgram.code).all()
    return [{"curriculum_id": item.course_id, "code": item.code, "name": item.course_name,
             "status": item.status} for item in programs]


@router.post("", response_model=SubjectResponse, status_code=201)
def create_subject(data: SubjectRequest, db: Session = Depends(get_db)):
    subject = Subject()
    apply_fields(subject, data)
    db.add(subject); commit_subject(db); db.refresh(subject)
    return serialize_subjects(db, [subject])[0]


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    return serialize_subjects(db, [find_subject(db, subject_id)])[0]


@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject(subject_id: int, data: SubjectRequest, db: Session = Depends(get_db)):
    subject = find_subject(db, subject_id, lock=True)
    check_subject_capacity(db, subject_id, data.session_count)
    apply_fields(subject, data)
    commit_subject(db); db.refresh(subject)
    return serialize_subjects(db, [subject])[0]


@router.put("/{subject_id}/programs", response_model=SubjectResponse,
            dependencies=[Depends(require_permission("CURRICULUM_MANAGE"))])
def set_subject_programs(subject_id: int, data: SubjectProgramsRequest, db: Session = Depends(get_db)):
    subject = find_subject(db, subject_id, lock=True)
    selected = set(data.curriculum_ids)
    current_program_ids = {row[0] for row in db.query(CurriculumSubject.curriculum_id).filter(CurriculumSubject.subject_id == subject_id)}
    programs = db.query(TrainingProgram).filter(TrainingProgram.course_id.in_(current_program_ids | selected)).order_by(TrainingProgram.course_id).with_for_update().all()
    if {program.course_id for program in programs if program.deleted_at is None and program.course_id in selected} != selected:
        raise HTTPException(status_code=404, detail="Một chương trình không còn tồn tại. Vui lòng tải lại danh sách.")
    capture_class_usage(db, subject_id)
    current = db.query(CurriculumSubject).filter(CurriculumSubject.subject_id == subject_id).all()
    removed = [item for item in current if item.curriculum_id not in selected]
    for item in removed:
        if db.query(CurriculumSubject).filter(CurriculumSubject.curriculum_id == item.curriculum_id,
                                             CurriculumSubject.prerequisite_subject_id == subject_id).first():
            raise HTTPException(status_code=409, detail="Môn đang là môn tiên quyết trong chương trình nên chưa thể gỡ.")
        db.delete(item)
    existing_ids = {item.curriculum_id for item in current}
    for program_id in sorted(selected - existing_ids):
        last = db.query(func.max(CurriculumSubject.sequence_order)).filter(CurriculumSubject.curriculum_id == program_id).scalar() or 0
        db.add(CurriculumSubject(curriculum_id=program_id, subject_id=subject_id, sequence_order=last + 1))
    db.flush(); capture_class_usage(db, subject_id)
    for program_id in sorted(current_program_ids | selected):
        normalize_program_order(db, program_id)
    db.commit()
    return serialize_subjects(db, [subject])[0]


@router.delete("/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = find_subject(db, subject_id, lock=True)
    program_ids = {row[0] for row in db.query(CurriculumSubject.curriculum_id).filter(CurriculumSubject.subject_id == subject_id)}
    db.query(TrainingProgram).filter(TrainingProgram.course_id.in_(program_ids)).order_by(TrainingProgram.course_id).with_for_update().all()
    usage = class_usage_query(db)
    if db.query(usage).filter(usage.c.subject_id == subject_id).first():
        raise HTTPException(status_code=409, detail="Môn học đã có lớp học nên không được xóa, kể cả lớp đã kết thúc.")
    if db.query(CurriculumSubject).filter(CurriculumSubject.prerequisite_subject_id == subject_id).first():
        raise HTTPException(status_code=409, detail="Môn đang được dùng làm môn tiên quyết nên chưa thể xóa.")
    db.query(CurriculumSubject).filter(CurriculumSubject.subject_id == subject_id).delete(synchronize_session=False)
    subject.deleted_at = datetime.now()
    for program_id in sorted(program_ids):
        normalize_program_order(db, program_id)
    db.commit()
    return {"message": "Đã xóa môn học khỏi danh mục.", "subject_id": subject_id}
