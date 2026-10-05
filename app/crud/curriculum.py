from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.curriculum import CurriculumSubject
from app.schemas.curriculum import CurriculumSubjectCreate, CurriculumSubjectReorder

# 1. Thêm môn học vào chương trình
def add_subject_to_curriculum(db: Session, curriculum_id: int, data: CurriculumSubjectCreate):
    # Kiểm tra trùng lặp
    existing = db.query(CurriculumSubject).filter(
        CurriculumSubject.curriculum_id == curriculum_id,
        CurriculumSubject.subject_id == data.subject_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Môn học này đã có trong chương trình!")

    # Validate môn tiên quyết không được trùng với chính nó
    if data.prerequisite_subject_id and data.prerequisite_subject_id == data.subject_id:
        raise HTTPException(status_code=400, detail="Môn tiên quyết không thể là chính môn học này!")

    new_item = CurriculumSubject(
        curriculum_id=curriculum_id,
        subject_id=data.subject_id,
        sequence_order=data.sequence_order,
        prerequisite_subject_id=data.prerequisite_subject_id
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
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
    return db.query(CurriculumSubject)\
             .filter(CurriculumSubject.curriculum_id == curriculum_id)\
             .order_by(CurriculumSubject.sequence_order.asc())\
             .all()