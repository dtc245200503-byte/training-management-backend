from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.crud.subjects import find_subject
from app.models.subject_lesson import SubjectLesson


def lessons_query(db, subject_id):
    return db.query(SubjectLesson).filter(SubjectLesson.subject_id == subject_id)


def serialize_lessons(db, subject):
    return {"subject_id": subject.id, "code": subject.code, "name": subject.subject_name,
            "session_count": subject.session_count,
            "items": [{"lesson_id": lesson.id, "sequence_order": lesson.sequence_order,
                       "topic": lesson.topic, "objectives": lesson.objectives}
                      for lesson in lessons_query(db, subject.id).order_by(SubjectLesson.sequence_order).all()]}


def check_subject_capacity(db, subject_id, session_count):
    last = lessons_query(db, subject_id).with_entities(func.max(SubjectLesson.sequence_order)).scalar() or 0
    if last > session_count:
        raise HTTPException(status_code=409, detail="Không thể giảm số buổi của môn xuống dưới số thứ tự buổi đã khai báo. Hãy sửa hoặc gỡ các buổi vượt giới hạn trước.")


def commit_lessons(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Số thứ tự buổi học đã tồn tại trong môn. Vui lòng tải lại danh sách.")


def save_lesson(db, subject_id, data, lesson_id=None):
    subject = find_subject(db, subject_id, lock=True)
    lesson = None
    if lesson_id is not None:
        lesson = lessons_query(db, subject_id).filter(SubjectLesson.id == lesson_id).first()
        if lesson is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy buổi học trong môn này.")
    if data.sequence_order > subject.session_count:
        raise HTTPException(status_code=400, detail=f"Số thứ tự buổi học không được vượt quá {subject.session_count} buổi của môn.")
    duplicate = lessons_query(db, subject_id).filter(SubjectLesson.sequence_order == data.sequence_order)
    if lesson is not None:
        duplicate = duplicate.filter(SubjectLesson.id != lesson.id)
    if duplicate.first():
        raise HTTPException(status_code=409, detail="Số thứ tự buổi học đã tồn tại trong môn.")
    if lesson is None:
        if lessons_query(db, subject_id).count() >= subject.session_count:
            raise HTTPException(status_code=400, detail="Môn đã khai báo đủ số buổi học.")
        lesson = SubjectLesson(subject_id=subject_id)
        db.add(lesson)
    lesson.sequence_order = data.sequence_order
    lesson.topic = data.topic
    lesson.objectives = data.objectives
    commit_lessons(db)
    db.refresh(lesson)
    return {"lesson_id": lesson.id, "sequence_order": lesson.sequence_order,
            "topic": lesson.topic, "objectives": lesson.objectives}


def clone_lessons(db, subject_id, data):
    if subject_id == data.source_subject_id:
        raise HTTPException(status_code=400, detail="Vui lòng chọn một môn khác để nhân bản buổi học.")
    # Lock both subjects in a stable order, including clones in opposite directions.
    subjects = {sid: find_subject(db, sid, lock=True) for sid in sorted([subject_id, data.source_subject_id])}
    source = lessons_query(db, data.source_subject_id).order_by(SubjectLesson.sequence_order).all()
    if not source:
        raise HTTPException(status_code=400, detail="Môn nguồn chưa khai báo buổi học để nhân bản.")
    target = subjects[subject_id]
    existing = lessons_query(db, subject_id).order_by(SubjectLesson.sequence_order).all()
    start = (existing[-1].sequence_order if existing else 0) if data.mode == "append" else 0
    if start + len(source) > target.session_count:
        raise HTTPException(status_code=400, detail="Danh sách nhân bản vượt quá số buổi của môn đích. Hãy tăng số buổi của môn hoặc chọn thay thế danh sách nếu phù hợp.")
    # Snapshot independent values before any mutation; source rows stay untouched.
    copies = [(lesson.topic, lesson.objectives) for lesson in source]
    if data.mode == "replace":
        for lesson in existing:
            db.delete(lesson)
        db.flush()
    db.add_all([SubjectLesson(subject_id=subject_id, sequence_order=start + offset, topic=topic, objectives=objectives)
                for offset, (topic, objectives) in enumerate(copies, 1)])
    commit_lessons(db)
    return serialize_lessons(db, target)
