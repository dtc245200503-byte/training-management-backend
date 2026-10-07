from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.training_program import ProgramSubject, TrainingProgram
from app.repositories.subject_repository import SubjectRepository
from app.repositories.training_program_repository import TrainingProgramRepository
from app.schemas.subject import SubjectResponse
from app.schemas.training_program import (
    AttachSubjectRequest,
    AttachedSubjectResponse,
    TrainingProgramCreate,
    TrainingProgramListResponse,
    TrainingProgramResponse,
    TrainingProgramUpdate,
)


class TrainingProgramService:
    def __init__(self, db: Session):
        self.db = db
        self.program_repo = TrainingProgramRepository(db)
        self.subject_repo = SubjectRepository(db)

    def _to_program_response(self, program: TrainingProgram) -> TrainingProgramResponse:
        attached = []
        if program.program_subjects:
            for ps in program.program_subjects:
                attached.append(
                    AttachedSubjectResponse(
                        id=ps.id,
                        subject_id=ps.subject_id,
                        order_index=ps.order_index,
                        is_mandatory=ps.is_mandatory,
                        subject=SubjectResponse.model_validate(ps.subject),
                    )
                )
        return TrainingProgramResponse(
            id=program.id,
            code=program.code,
            name=program.name,
            description=program.description,
            duration_hours=program.duration_hours,
            status=program.status,
            created_at=program.created_at,
            updated_at=program.updated_at,
            program_subjects=attached,
        )

    # =========================================================================
    # S2-04: Training Program CRUD
    # =========================================================================
    def list_programs(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> TrainingProgramListResponse:
        items, total = self.program_repo.get_all(
            skip=skip,
            limit=limit,
            search=search,
            status=status_filter,
        )
        return TrainingProgramListResponse(
            total=total,
            items=[self._to_program_response(p) for p in items],
        )

    def get_program(self, program_id: int) -> TrainingProgramResponse:
        program = self.program_repo.get_by_id(program_id)
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chương trình đào tạo.",
            )
        return self._to_program_response(program)

    def create_program(self, request: TrainingProgramCreate) -> TrainingProgramResponse:
        code_clean = request.code.strip().upper()
        if self.program_repo.get_by_code(code_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã chương trình '{code_clean}' đã tồn tại trong hệ thống.",
            )

        program = TrainingProgram(
            code=code_clean,
            name=request.name.strip(),
            description=request.description.strip() if request.description else None,
            duration_hours=request.duration_hours,
            status=request.status.strip().upper(),
        )
        self.program_repo.create(program)
        return self._to_program_response(program)

    def update_program(self, program_id: int, request: TrainingProgramUpdate) -> TrainingProgramResponse:
        program = self.program_repo.get_by_id(program_id)
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chương trình đào tạo.",
            )

        if request.name is not None:
            program.name = request.name.strip()
        if request.description is not None:
            program.description = request.description.strip()
        if request.duration_hours is not None:
            program.duration_hours = request.duration_hours
        if request.status is not None:
            program.status = request.status.strip().upper()

        program.updated_at = datetime.now(timezone.utc)
        self.program_repo.update(program)
        return self._to_program_response(program)

    def delete_program(self, program_id: int) -> dict:
        program = self.program_repo.get_by_id(program_id)
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chương trình đào tạo.",
            )
        self.program_repo.delete(program)
        return {"message": "Xóa chương trình đào tạo thành công."}

    # =========================================================================
    # S2-06: Attach Subjects to Training Program
    # =========================================================================
    def list_attached_subjects(self, program_id: int) -> List[AttachedSubjectResponse]:
        program = self.program_repo.get_by_id(program_id)
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chương trình đào tạo.",
            )
        attached = []
        for ps in program.program_subjects:
            attached.append(
                AttachedSubjectResponse(
                    id=ps.id,
                    subject_id=ps.subject_id,
                    order_index=ps.order_index,
                    is_mandatory=ps.is_mandatory,
                    subject=SubjectResponse.model_validate(ps.subject),
                )
            )
        return attached

    def attach_subject(self, program_id: int, request: AttachSubjectRequest) -> AttachedSubjectResponse:
        program = self.program_repo.get_by_id(program_id)
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chương trình đào tạo.",
            )

        subject = self.subject_repo.get_by_id(request.subject_id)
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy môn học có ID {request.subject_id}.",
            )

        existing = self.program_repo.get_attached_subject(program_id, request.subject_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Môn học này đã được gán vào chương trình đào tạo từ trước.",
            )

        link = self.program_repo.attach_subject(
            program_id=program_id,
            subject_id=request.subject_id,
            order_index=request.order_index or 0,
            is_mandatory=True if request.is_mandatory is None else request.is_mandatory,
        )

        return AttachedSubjectResponse(
            id=link.id,
            subject_id=link.subject_id,
            order_index=link.order_index,
            is_mandatory=link.is_mandatory,
            subject=SubjectResponse.model_validate(subject),
        )

    def detach_subject(self, program_id: int, subject_id: int) -> dict:
        program = self.program_repo.get_by_id(program_id)
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy chương trình đào tạo.",
            )

        link = self.program_repo.get_attached_subject(program_id, subject_id)
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Môn học không nằm trong chương trình đào tạo này.",
            )

        self.program_repo.detach_subject(program_id, subject_id)
        return {"message": "Gỡ môn học khỏi chương trình đào tạo thành công."}
