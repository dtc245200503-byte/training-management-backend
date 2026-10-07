from datetime import datetime, timezone
import os
from pathlib import Path
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.profile import AvatarUploadResponse, UserProfileDetail, UserProfileUpdate

# Thư mục lưu trữ avatar người dùng
UPLOAD_DIR = Path("uploads/avatars")


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def _to_profile_detail(self, user: User) -> UserProfileDetail:
        return UserProfileDetail(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            avatar_url=user.avatar_url,
            bio=user.bio,
            address=user.address,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            is_active=user.is_active,
            is_locked=user.is_locked,
            roles=user.role_names,
            permissions=user.permission_codes,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def get_profile(self, user: User) -> UserProfileDetail:
        return self._to_profile_detail(user)

    def update_profile(self, user: User, request: UserProfileUpdate) -> UserProfileDetail:
        if request.full_name is not None:
            user.full_name = request.full_name
        if request.phone_number is not None:
            user.phone_number = request.phone_number
        if request.bio is not None:
            user.bio = request.bio
        if request.address is not None:
            user.address = request.address
        if request.date_of_birth is not None:
            user.date_of_birth = request.date_of_birth
        if request.gender is not None:
            user.gender = request.gender

        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)
        return self._to_profile_detail(user)

    def upload_avatar(self, user: User, file: UploadFile) -> AvatarUploadResponse:
        # 1. Kiểm tra định dạng file ảnh hợp lệ
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_content_types = {"image/jpeg", "image/png", "image/webp"}

        original_filename = file.filename or ""
        ext = os.path.splitext(original_filename)[1].lower()

        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Định dạng file không hỗ trợ ({ext}). Chỉ chấp nhận file ảnh: .jpg, .jpeg, .png, .webp.",
            )

        if file.content_type and file.content_type.lower() not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Loại nội dung (content-type) không hợp lệ cho hình ảnh.",
            )

        # 2. Đọc và kiểm tra kích thước file (tối đa 5MB)
        content = file.file.read()
        max_size = 5 * 1024 * 1024  # 5MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kích thước file ảnh vượt quá giới hạn tối đa cho phép (5MB).",
            )
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File tải lên không có dữ liệu (file rỗng).",
            )

        # 3. Lưu trữ an toàn: tạo tên file ngẫu nhiên UUID chống path traversal
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{uuid.uuid4().hex}{ext}"
        target_path = UPLOAD_DIR / safe_filename

        with open(target_path, "wb") as f:
            f.write(content)

        # 4. Cập nhật avatar_url trong database
        avatar_url = f"/uploads/avatars/{safe_filename}"
        user.avatar_url = avatar_url
        user.updated_at = datetime.now(timezone.utc)
        self.user_repo.update(user)

        return AvatarUploadResponse(
            message="Tải lên ảnh đại diện thành công.",
            avatar_url=avatar_url,
        )
