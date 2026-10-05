from sqlalchemy.orm import Session, aliased
from fastapi import HTTPException, status
from app.models.curriculum import CurriculumSubject
from app.schemas.curriculum import CurriculumSubjectCreate, CurriculumSubjectReorder
from app.models.subject import Subject

# 1. Thêm môn học vào chương trình
def add_subject_to_curriculum(db: Session, curriculum_id: int, data: CurriculumSubjectCreate):
    # Kiểm tra trùng lặp trong lộ trình
    existing = db.query(CurriculumSubject).filter(
        CurriculumSubject.curriculum_id == curriculum_id,
        CurriculumSubject.subject_id == data.subject_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Môn học này đã có trong chương trình!")

    # Validate môn tiên quyết không được trùng với chính nó
    if data.prerequisite_subject_id and data.prerequisite_subject_id == data.subject_id:
        raise HTTPException(status_code=400, detail="Môn tiên quyết không thể là chính môn học này!")

    # --- XỬ LÝ LƯU/CẬP NHẬT BẢNG SUBJECTS ---
    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not subject:
        # Nếu môn học chưa có trong DB, tạo bản ghi mới trong bảng subjects
        subject = Subject(
            id=data.subject_id,
            subject_name=data.subject_name or f"Môn học #{data.subject_id}"
        )
        db.add(subject)
    elif data.subject_name:
        # Nếu đã có môn học nhưng người dùng nhập/sửa tên mới -> cập nhật tên
        subject.subject_name = data.subject_name

    # --- LƯU VÀO BẢNG TẬP HỢP LỘ TRÌNH CURRICULUM_SUBJECTS ---
    new_item = CurriculumSubject(
        curriculum_id=curriculum_id,
        subject_id=data.subject_id,
        sequence_order=data.sequence_order,
        prerequisite_subject_id=data.prerequisite_subject_id
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    # --- GÁN THUỘC TÍNH ĐỂ SCHEMAS SERIALIZE VỀ FRONTEND ---
    new_item.subject_name = subject.subject_name

    if data.prerequisite_subject_id:
        prereq = db.query(Subject).filter(Subject.id == data.prerequisite_subject_id).first()
        new_item.prerequisite_subject_name = prereq.subject_name if prereq else None
    else:
        new_item.prerequisite_subject_name = None

    return new_item

# 2. Gỡ môn học khỏi chương trình
def remove_subject_from_curriculum(db: Session, curriculum_id: int, subject_id: int):
    item = db.query(CurriculumSubject).filter(
        CurriculumSubject.curriculum_id == curriculum_id,
        CurriculumSubject.subject_id == subject_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học trong chương trình!")
    
    db.delete(item)
    db.commit()
    return {"message": "Đã xóa môn học khỏi chương trình"}

# 3. Cập nhật thứ tự (Drag-and-drop)
def reorder_curriculum_subjects(db: Session, curriculum_id: int, reorder_data: CurriculumSubjectReorder):
    for item in reorder_data.items:
        db.query(CurriculumSubject).filter(
            CurriculumSubject.curriculum_id == curriculum_id,
            CurriculumSubject.subject_id == item.subject_id
        ).update({"sequence_order": item.sequence_order})
    
    db.commit()
    return {"message": "Cập nhật thứ tự môn học thành công"}

# 4. Lấy danh sách môn học theo lộ trình
def get_curriculum_subjects(db: Session, curriculum_id: int):
    PrereqSubject = aliased(Subject)

    results = (
        db.query(
            CurriculumSubject,
            Subject.subject_name.label("subject_name"),
            PrereqSubject.subject_name.label("prerequisite_subject_name")
        )
        .join(Subject, CurriculumSubject.subject_id == Subject.id)
        .outerjoin(PrereqSubject, CurriculumSubject.prerequisite_subject_id == PrereqSubject.id)
        .filter(CurriculumSubject.curriculum_id == curriculum_id)
        .order_by(CurriculumSubject.sequence_order)
        .all()
    )

    subjects_list = []
    for item, subject_name, prereq_name in results:
        item.subject_name = subject_name
        item.prerequisite_subject_name = prereq_name
        subjects_list.append(item)

    return subjects_list