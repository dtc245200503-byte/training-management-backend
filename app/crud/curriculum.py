from sqlalchemy.orm import Session, aliased
from fastapi import HTTPException
from app.models.curriculum import CurriculumSubject
from app.schemas.curriculum import CurriculumSubjectCreate, CurriculumSubjectReorder
from app.models.subject import Subject
from app.crud.subjects import find_subject, capture_class_usage
from app.routers.training_programs import find_program


def ordered_links(db, curriculum_id):
    return db.query(CurriculumSubject).filter(CurriculumSubject.curriculum_id == curriculum_id).order_by(
        CurriculumSubject.sequence_order, CurriculumSubject.id).populate_existing().with_for_update().all()


def validate_learning_path(items):
    """Strictly earlier prerequisites also rule out every dependency cycle."""
    positions = {item.subject_id: index for index, item in enumerate(items)}
    for item in items:
        prerequisite = item.prerequisite_subject_id
        if prerequisite is None:
            continue
        if prerequisite == item.subject_id:
            raise HTTPException(status_code=400, detail="Môn tiên quyết không thể là chính môn học này.")
        if prerequisite not in positions:
            raise HTTPException(status_code=400, detail="Môn tiên quyết phải có trong cùng chương trình.")
        if positions[prerequisite] >= positions[item.subject_id]:
            raise HTTPException(status_code=400, detail="Môn tiên quyết phải đứng trước môn phụ thuộc trong lộ trình. Không được tạo vòng phụ thuộc.")


def persist_positions(items):
    for position, item in enumerate(items, 1):
        item.sequence_order = position


def normalize_program_order(db, curriculum_id):
    persist_positions(ordered_links(db, curriculum_id))

# 1. Thêm môn học vào chương trình
def add_subject_to_curriculum(db: Session, curriculum_id: int, data: CurriculumSubjectCreate):
    find_subject(db, data.subject_id, lock=True)
    find_program(db, curriculum_id, lock=True)
    items = ordered_links(db, curriculum_id)
    if any(item.subject_id == data.subject_id for item in items):
        raise HTTPException(status_code=400, detail="Môn học này đã có trong chương trình!")
    position = data.sequence_order if data.sequence_order is not None else len(items) + 1
    if position > len(items) + 1:
        raise HTTPException(status_code=400, detail="Vị trí thêm môn vượt quá số môn của chương trình.")
    if data.prerequisite_subject_id:
        find_subject(db, data.prerequisite_subject_id)
    new_item = CurriculumSubject(
        curriculum_id=curriculum_id,
        subject_id=data.subject_id,
        sequence_order=position,
        prerequisite_subject_id=data.prerequisite_subject_id
    )
    items.insert(position - 1, new_item)
    validate_learning_path(items)
    persist_positions(items)
    db.add(new_item)
    db.flush()
    capture_class_usage(db, data.subject_id)
    db.commit()
    return next(item for item in get_curriculum_subjects(db, curriculum_id) if item.subject_id == data.subject_id)

# 2. Gỡ môn học khỏi chương trình
def remove_subject_from_curriculum(db: Session, curriculum_id: int, subject_id: int):
    find_subject(db, subject_id, lock=True)
    find_program(db, curriculum_id, lock=True)
    item = db.query(CurriculumSubject).filter(
        CurriculumSubject.curriculum_id == curriculum_id,
        CurriculumSubject.subject_id == subject_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học trong chương trình!")
    
    if db.query(CurriculumSubject).filter(CurriculumSubject.curriculum_id == curriculum_id,
                                         CurriculumSubject.prerequisite_subject_id == subject_id).first():
        raise HTTPException(status_code=409, detail="Môn đang là môn tiên quyết nên chưa thể gỡ khỏi chương trình.")
    capture_class_usage(db, subject_id)
    db.delete(item)
    db.flush()
    normalize_program_order(db, curriculum_id)
    db.commit()
    return {"message": "Đã xóa môn học khỏi chương trình"}

# 3. Cập nhật thứ tự (Drag-and-drop)
def reorder_curriculum_subjects(db: Session, curriculum_id: int, reorder_data: CurriculumSubjectReorder):
    find_program(db, curriculum_id, lock=True)
    current = ordered_links(db, curriculum_id)
    ids = [item.subject_id for item in reorder_data.items]
    positions = [item.sequence_order for item in reorder_data.items]
    if len(set(ids)) != len(ids) or sorted(positions) != list(range(1, len(ids) + 1)):
        raise HTTPException(status_code=400, detail="Mỗi môn cần một vị trí duy nhất, liên tục từ 1.")
    by_id = {item.subject_id: item for item in current}
    if set(ids) != set(by_id):
        raise HTTPException(status_code=409, detail="Danh sách môn đã thay đổi hoặc không thuộc chương trình. Vui lòng tải lại lộ trình.")
    ordered = [by_id[item.subject_id] for item in sorted(reorder_data.items, key=lambda item: item.sequence_order)]
    validate_learning_path(ordered)
    persist_positions(ordered)
    db.commit()
    return {"message": "Đã lưu thứ tự học.", "items": get_curriculum_subjects(db, curriculum_id)}


def update_prerequisite(db, curriculum_id, subject_id, data):
    find_program(db, curriculum_id, lock=True)
    items = ordered_links(db, curriculum_id)
    item = next((item for item in items if item.subject_id == subject_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học trong chương trình.")
    if data.prerequisite_subject_id is not None:
        find_subject(db, data.prerequisite_subject_id)
    item.prerequisite_subject_id = data.prerequisite_subject_id
    validate_learning_path(items)
    persist_positions(items)
    db.commit()
    return next(item for item in get_curriculum_subjects(db, curriculum_id) if item.subject_id == subject_id)

# 4. Lấy danh sách môn học theo lộ trình
def get_curriculum_subjects(db: Session, curriculum_id: int):
    find_program(db, curriculum_id)
    PrereqSubject = aliased(Subject)

    results = (
        db.query(
            CurriculumSubject,
            Subject,
            Subject.subject_name.label("subject_name"),
            PrereqSubject.subject_name.label("prerequisite_subject_name")
        )
        .join(Subject, CurriculumSubject.subject_id == Subject.id)
        .outerjoin(PrereqSubject, CurriculumSubject.prerequisite_subject_id == PrereqSubject.id)
        .filter(CurriculumSubject.curriculum_id == curriculum_id, Subject.deleted_at.is_(None))
        .order_by(CurriculumSubject.sequence_order, CurriculumSubject.id)
        .all()
    )

    subjects_list = []
    for item, subject, subject_name, prereq_name in results:
        item.subject_name = subject_name
        item.subject_code = subject.code
        item.session_count = subject.session_count
        item.weight = subject.weight
        item.learning_outcomes = subject.description
        item.prerequisite_subject_name = prereq_name
        subjects_list.append(item)

    return subjects_list
