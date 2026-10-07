from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.training_session import (
    TrainingSessionCreate,
    TrainingSessionListResponse,
    TrainingSessionResponse,
    TrainingSessionUpdate,
)
from app.security.dependencies import get_current_user, require_permissions
from app.services.training_session_service import TrainingSessionService

router = APIRouter(prefix="/api/training-sessions", tags=["Training Sessions"])


@router.get(
    "",
    response_model=TrainingSessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách lớp/phiên đào tạo",
    description="Lấy danh sách các lớp đào tạo có lọc theo chương trình, môn học, giảng viên, trạng thái.",
)
def list_training_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    program_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    trainer_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TrainingSessionService(db)
    return service.list_sessions(
        skip=skip,
        limit=limit,
        search=search,
        status_filter=status,
        program_id=program_id,
        subject_id=subject_id,
        trainer_id=trainer_id,
    )


@router.get(
    "/{session_id}",
    response_model=TrainingSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết lớp/phiên đào tạo",
    description="Lấy thông tin chi tiết một phiên đào tạo theo ID.",
)
def get_training_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TrainingSessionService(db)
    return service.get_session(session_id)


@router.post(
    "",
    response_model=TrainingSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo lớp/phiên đào tạo mới",
    description="Tạo một phiên đào tạo mới với ràng buộc thời gian và giảng viên hợp lệ.",
)
def create_training_session(
    request: TrainingSessionCreate,
    current_user: User = Depends(require_permissions("session:manage")),
    db: Session = Depends(get_db),
):
    service = TrainingSessionService(db)
    return service.create_session(request)


@router.put(
    "/{session_id}",
    response_model=TrainingSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật lớp/phiên đào tạo",
    description="Cập nhật thông tin phiên đào tạo theo ID.",
)
def update_training_session(
    session_id: int,
    request: TrainingSessionUpdate,
    current_user: User = Depends(require_permissions("session:manage")),
    db: Session = Depends(get_db),
):
    service = TrainingSessionService(db)
    return service.update_session(session_id, request)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa lớp/phiên đào tạo",
    description="Xóa phiên đào tạo khỏi hệ thống.",
)
def delete_training_session(
    session_id: int,
    current_user: User = Depends(require_permissions("session:manage")),
    db: Session = Depends(get_db),
):
    service = TrainingSessionService(db)
    return service.delete_session(session_id)
