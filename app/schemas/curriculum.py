from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Schema khi thêm môn học vào chương trình
class CurriculumSubjectCreate(BaseModel):
    subject_id: int
    subject_name: Optional[str] = None  # <--- BỔ SUNG DÒNG NÀY
    sequence_order: Optional[int] = 1
    prerequisite_subject_id: Optional[int] = None

# Schema cập nhật thứ tự (dùng cho Drag-and-drop)
class SubjectOrderItem(BaseModel):
    subject_id: int
    sequence_order: int

class CurriculumSubjectReorder(BaseModel):
    items: List[SubjectOrderItem]

# Schema trả về kết quả
class CurriculumSubjectResponse(BaseModel):
    id: int
    curriculum_id: int
    subject_id: int
    subject_name: Optional[str] = None
    sequence_order: int
    prerequisite_subject_id: Optional[int] = None
    prerequisite_subject_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True