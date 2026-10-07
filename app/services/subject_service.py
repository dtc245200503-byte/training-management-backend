from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.subject import Subject
from app.repositories.subject_repository import SubjectRepository
from app.schemas.subject import SubjectCreate, SubjectListResponse, SubjectResponse, SubjectUpdate


class SubjectService:
    def __init__(self, db: Session):
        self.db = db
        self.subject_repo = SubjectRepository(db)

    def list_subjects(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> SubjectListResponse:
        items, total = self.subject_repo.get_all(
            skip=skip,
            limit=limit,
            search=search,
            status=status_filter,
        )
        return SubjectListResponse(
            total=total,
            items=[SubjectResponse.model_validate(s) for s in items],
        )

    def get_subject(self, subject_id: int) -> SubjectResponse:
        subject = self.subject_repo.get_by_id(subject_id)
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy môn học.",
            )
        return SubjectResponse.model_validate(subject)

    def create_subject(self, request: SubjectCreate) -> SubjectResponse:
        code_clean = request.code.strip().upper()
        if self.subject_repo.get_by_code(code_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã môn học '{code_clean}' đã tồn tại trong hệ thống.",
            )

        subject = Subject(
            code=code_clean,
            name=request.name.strip(),
            description=request.description.strip() if request.description else None,
            hours=request.hours,
            status=request.status.strip().upper(),
        )
        self.subject_repo.create(subject)
        return SubjectResponse.model_validate(subject)

    def update_subject(self, subject_id: int, request: SubjectUpdate) -> SubjectResponse:
        subject = self.subject_repo.get_by_id(subject_id)
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy môn học.",
            )

        if request.name is not None:
            subject.name = request.name.strip()
        if request.description is not None:
            subject.description = request.description.strip()
        if request.hours is not None:
            subject.hours = request.hours
        if request.status is not None:
            subject.status = request.status.strip().upper()

        subject.updated_at = datetime.now(timezone.utc)
        self.subject_repo.update(subject)
        return SubjectResponse.model_validate(subject)

    def delete_subject(self, subject_id: int) -> dict:
        subject = self.subject_repo.get_by_id(subject_id)
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy môn học.",
            )
        self.subject_repo.delete(subject)
        return {"message": "Xóa môn học thành công."}
