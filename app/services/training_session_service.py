from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.training_session import TrainingSession
from app.repositories.subject_repository import SubjectRepository
from app.repositories.training_program_repository import TrainingProgramRepository
from app.repositories.training_session_repository import TrainingSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.training_session import (
    TrainingSessionCreate,
    TrainingSessionListResponse,
    TrainingSessionResponse,
    TrainingSessionUpdate,
)


class TrainingSessionService:
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = TrainingSessionRepository(db)
        self.program_repo = TrainingProgramRepository(db)
        self.subject_repo = SubjectRepository(db)
        self.user_repo = UserRepository(db)

    @staticmethod
    def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _to_session_response(self, session: TrainingSession) -> TrainingSessionResponse:
        return TrainingSessionResponse(
            id=session.id,
            code=session.code,
            name=session.name,
            program_id=session.program_id,
            program_name=session.program.name if session.program else None,
            subject_id=session.subject_id,
            subject_name=session.subject.name if session.subject else None,
            trainer_id=session.trainer_id,
            trainer_name=session.trainer.full_name if session.trainer else None,
            start_date=session.start_date,
            end_date=session.end_date,
            location=session.location,
            max_trainees=session.max_trainees,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def list_sessions(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        program_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        trainer_id: Optional[int] = None,
    ) -> TrainingSessionListResponse:
        items, total = self.session_repo.get_all(
            skip=skip,
            limit=limit,
            search=search,
            status=status_filter,
            program_id=program_id,
            subject_id=subject_id,
            trainer_id=trainer_id,
        )
        return TrainingSessionListResponse(
            total=total,
            items=[self._to_session_response(s) for s in items],
        )

    def get_session(self, session_id: int) -> TrainingSessionResponse:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên/lớp đào tạo.",
            )
        return self._to_session_response(session)

    def create_session(self, request: TrainingSessionCreate) -> TrainingSessionResponse:
        code_clean = request.code.strip().upper()
        if self.session_repo.get_by_code(code_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã phiên đào tạo '{code_clean}' đã tồn tại trong hệ thống.",
            )

        start = self._normalize_dt(request.start_date)
        end = self._normalize_dt(request.end_date)
        if start and end and start > end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thời gian bắt đầu không được lớn hơn thời gian kết thúc.",
            )

        if request.program_id is not None:
            if not self.program_repo.get_by_id(request.program_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy chương trình đào tạo có ID {request.program_id}.",
                )

        if request.subject_id is not None:
            if not self.subject_repo.get_by_id(request.subject_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy môn học có ID {request.subject_id}.",
                )

        if request.trainer_id is not None:
            trainer = self.user_repo.get_by_id(request.trainer_id)
            if not trainer or not trainer.is_active or trainer.is_locked:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Giảng viên chỉ định không tồn tại hoặc đang bị khóa/vô hiệu hóa.",
                )

        session = TrainingSession(
            code=code_clean,
            name=request.name.strip(),
            program_id=request.program_id,
            subject_id=request.subject_id,
            trainer_id=request.trainer_id,
            start_date=request.start_date,
            end_date=request.end_date,
            location=request.location.strip() if request.location else None,
            max_trainees=request.max_trainees,
            status=request.status.strip().upper(),
        )
        self.session_repo.create(session)
        return self._to_session_response(session)

    def update_session(self, session_id: int, request: TrainingSessionUpdate) -> TrainingSessionResponse:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên/lớp đào tạo.",
            )

        start = self._normalize_dt(request.start_date if request.start_date is not None else session.start_date)
        end = self._normalize_dt(request.end_date if request.end_date is not None else session.end_date)
        if start and end and start > end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thời gian bắt đầu không được lớn hơn thời gian kết thúc.",
            )

        if request.program_id is not None:
            if not self.program_repo.get_by_id(request.program_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy chương trình đào tạo có ID {request.program_id}.",
                )
            session.program_id = request.program_id

        if request.subject_id is not None:
            if not self.subject_repo.get_by_id(request.subject_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy môn học có ID {request.subject_id}.",
                )
            session.subject_id = request.subject_id

        if request.trainer_id is not None:
            trainer = self.user_repo.get_by_id(request.trainer_id)
            if not trainer or not trainer.is_active or trainer.is_locked:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Giảng viên chỉ định không tồn tại hoặc đang bị khóa/vô hiệu hóa.",
                )
            session.trainer_id = request.trainer_id

        if request.name is not None:
            session.name = request.name.strip()
        if request.start_date is not None:
            session.start_date = request.start_date
        if request.end_date is not None:
            session.end_date = request.end_date
        if request.location is not None:
            session.location = request.location.strip()
        if request.max_trainees is not None:
            session.max_trainees = request.max_trainees
        if request.status is not None:
            session.status = request.status.strip().upper()

        session.updated_at = datetime.now(timezone.utc)
        self.session_repo.update(session)
        return self._to_session_response(session)

    def delete_session(self, session_id: int) -> dict:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên/lớp đào tạo.",
            )
        self.session_repo.delete(session)
        return {"message": "Xóa phiên/lớp đào tạo thành công."}
