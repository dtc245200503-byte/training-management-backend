from fastapi import HTTPException
from sqlalchemy import func
from app.models.subject import ClassSubject, Subject
from app.models.curriculum import CurriculumSubject
from app.models.training_program import TrainingClass, TrainingProgram


def find_subject(db, subject_id, lock=False):
    query = db.query(Subject).filter(Subject.id == subject_id, Subject.deleted_at.is_(None))
    if lock:
        query = query.with_for_update()
    subject = query.first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học.")
    return subject


def class_usage_query(db):
    direct = db.query(ClassSubject.subject_id.label("subject_id"), ClassSubject.class_id.label("class_id"))
    via_program = db.query(CurriculumSubject.subject_id.label("subject_id"), TrainingClass.class_id.label("class_id")).join(
        TrainingClass, TrainingClass.course_id == CurriculumSubject.curriculum_id)
    return direct.union(via_program).subquery()


def capture_class_usage(db, subject_id):
    """Call under the subject lock before removing/changing program membership."""
    class_ids = [row[0] for row in db.query(TrainingClass.class_id).join(
        CurriculumSubject, CurriculumSubject.curriculum_id == TrainingClass.course_id).filter(
            CurriculumSubject.subject_id == subject_id).distinct()]
    existing = {row[0] for row in db.query(ClassSubject.class_id).filter(ClassSubject.subject_id == subject_id)}
    db.add_all([ClassSubject(subject_id=subject_id, class_id=class_id) for class_id in class_ids if class_id not in existing])
    db.flush()


def serialize_subjects(db, subjects):
    ids = [subject.id for subject in subjects]
    if not ids:
        return []
    usage = class_usage_query(db)
    counts = dict(db.query(usage.c.subject_id, func.count(usage.c.class_id)).filter(
        usage.c.subject_id.in_(ids)).group_by(usage.c.subject_id).all())
    prerequisites = dict(db.query(CurriculumSubject.prerequisite_subject_id, func.count(CurriculumSubject.id)).filter(
        CurriculumSubject.prerequisite_subject_id.in_(ids)).group_by(CurriculumSubject.prerequisite_subject_id).all())
    programs = {}
    rows = db.query(CurriculumSubject.subject_id, TrainingProgram).join(
        TrainingProgram, TrainingProgram.course_id == CurriculumSubject.curriculum_id).filter(
            CurriculumSubject.subject_id.in_(ids)).order_by(TrainingProgram.course_id).all()
    for subject_id, program in rows:
        programs.setdefault(subject_id, []).append({"curriculum_id": program.course_id, "code": program.code,
            "name": program.course_name, "is_deleted": program.deleted_at is not None})
    return [{"subject_id": subject.id, "code": subject.code, "name": subject.subject_name,
             "session_count": subject.session_count, "weight": subject.weight, "learning_outcomes": subject.description,
             "class_count": counts.get(subject.id, 0), "prerequisite_count": prerequisites.get(subject.id, 0),
             "can_delete": counts.get(subject.id, 0) == 0 and prerequisites.get(subject.id, 0) == 0,
             "programs": programs.get(subject.id, [])} for subject in subjects]
