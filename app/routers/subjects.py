from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.subject import (
    SubjectCreate,
    SubjectListResponse,
    SubjectResponse,
    SubjectUpdate,
)
from app.security.dependencies import get_current_user, require_permissions
from app.services.subject_service import SubjectService

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])


@router.get(
    "",
    response_model=SubjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách môn học",
    description="Lấy danh sách các môn học trong hệ thống có hỗ trợ tìm kiếm và lọc trạng thái.",
)
def list_subjects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SubjectService(db)
    return service.list_subjects(
        skip=skip,
        limit=limit,
        search=search,
        status_filter=status,
    )


@router.get(
    "/{subject_id}",
    response_model=SubjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết môn học",
    description="Lấy thông tin chi tiết một môn học theo ID.",
)
def get_subject(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SubjectService(db)
    return service.get_subject(subject_id)


@router.post(
    "",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo môn học mới",
    description="Tạo môn học mới với mã môn học duy nhất.",
)
def create_subject(
    request: SubjectCreate,
    current_user: User = Depends(require_permissions("subject:manage")),
    db: Session = Depends(get_db),
):
    service = SubjectService(db)
    return service.create_subject(request)


@router.put(
    "/{subject_id}",
    response_model=SubjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật môn học",
    description="Cập nhật thông tin môn học theo ID.",
)
def update_subject(
    subject_id: int,
    request: SubjectUpdate,
    current_user: User = Depends(require_permissions("subject:manage")),
    db: Session = Depends(get_db),
):
    service = SubjectService(db)
    return service.update_subject(subject_id, request)


@router.delete(
    "/{subject_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa môn học",
    description="Xóa môn học khỏi hệ thống.",
)
def delete_subject(
    subject_id: int,
    current_user: User = Depends(require_permissions("subject:manage")),
    db: Session = Depends(get_db),
):
    service = SubjectService(db)
    return service.delete_subject(subject_id)
