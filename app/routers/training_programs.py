from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.training_program import (
    AttachSubjectRequest,
    AttachedSubjectResponse,
    TrainingProgramCreate,
    TrainingProgramListResponse,
    TrainingProgramResponse,
    TrainingProgramUpdate,
)
from app.security.dependencies import get_current_user, require_permissions
from app.services.training_program_service import TrainingProgramService

router = APIRouter(prefix="/api/training-programs", tags=["Training Programs"])


# =============================================================================
# S2-04: Training Programs CRUD
# =============================================================================
@router.get(
    "",
    response_model=TrainingProgramListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách chương trình đào tạo",
    description="Lấy danh sách các chương trình đào tạo có hỗ trợ tìm kiếm và lọc trạng thái.",
)
def list_training_programs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TrainingProgramService(db)
    return service.list_programs(
        skip=skip,
        limit=limit,
        search=search,
        status_filter=status,
    )


@router.get(
    "/{program_id}",
    response_model=TrainingProgramResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết chương trình đào tạo",
    description="Lấy thông tin chi tiết một chương trình đào tạo kèm danh sách môn học đã gắn.",
)
def get_training_program(
    program_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TrainingProgramService(db)
    return service.get_program(program_id)


@router.post(
    "",
    response_model=TrainingProgramResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo chương trình đào tạo mới",
    description="Tạo một chương trình đào tạo mới với mã chương trình duy nhất.",
)
def create_training_program(
    request: TrainingProgramCreate,
    current_user: User = Depends(require_permissions("program:manage")),
    db: Session = Depends(get_db),
):
    service = TrainingProgramService(db)
    return service.create_program(request)


@router.put(
    "/{program_id}",
    response_model=TrainingProgramResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật chương trình đào tạo",
    description="Cập nhật thông tin chương trình đào tạo theo ID.",
)
def update_training_program(
    program_id: int,
    request: TrainingProgramUpdate,
    current_user: User = Depends(require_permissions("program:manage")),
    db: Session = Depends(get_db),
):
    service = TrainingProgramService(db)
    return service.update_program(program_id, request)


@router.delete(
    "/{program_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa chương trình đào tạo",
    description="Xóa chương trình đào tạo khỏi hệ thống.",
)
def delete_training_program(
    program_id: int,
    current_user: User = Depends(require_permissions("program:manage")),
    db: Session = Depends(get_db),
):
    service = TrainingProgramService(db)
    return service.delete_program(program_id)


# =============================================================================
# S2-06: Gắn / Gỡ môn học vào chương trình đào tạo
# =============================================================================
@router.get(
    "/{program_id}/subjects",
    response_model=List[AttachedSubjectResponse],
    status_code=status.HTTP_200_OK,
    summary="Danh sách môn học thuộc chương trình",
    description="Lấy danh sách các môn học đã được gắn vào chương trình đào tạo này.",
)
def list_attached_subjects(
    program_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TrainingProgramService(db)
    return service.list_attached_subjects(program_id)


@router.post(
    "/{program_id}/subjects",
    response_model=AttachedSubjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Gắn môn học vào chương trình đào tạo",
    description="Gắn môn học vào chương trình đào tạo kèm thứ tự và cấu hình bắt buộc/tự chọn.",
)
def attach_subject(
    program_id: int,
    request: AttachSubjectRequest,
    current_user: User = Depends(require_permissions("program:manage")),
    db: Session = Depends(get_db),
):
    service = TrainingProgramService(db)
    return service.attach_subject(program_id, request)


@router.delete(
    "/{program_id}/subjects/{subject_id}",
    status_code=status.HTTP_200_OK,
    summary="Gỡ môn học khỏi chương trình đào tạo",
    description="Gỡ bỏ một môn học khỏi chương trình đào tạo đã chỉ định.",
)
def detach_subject(
    program_id: int,
    subject_id: int,
    current_user: User = Depends(require_permissions("program:manage")),
    db: Session = Depends(get_db),
):
    service = TrainingProgramService(db)
    return service.detach_subject(program_id, subject_id)
