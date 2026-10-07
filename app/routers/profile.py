from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.profile import AvatarUploadResponse, UserProfileDetail, UserProfileUpdate
from app.security.dependencies import get_current_user
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/api/profile", tags=["User Profile"])


@router.get(
    "",
    response_model=UserProfileDetail,
    status_code=status.HTTP_200_OK,
    summary="Xem thông tin hồ sơ cá nhân",
    description="Lấy thông tin chi tiết hồ sơ của người dùng hiện đang đăng nhập.",
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    return service.get_profile(current_user)


@router.put(
    "",
    response_model=UserProfileDetail,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật hồ sơ cá nhân",
    description="Cập nhật họ tên, số điện thoại, tiểu sử, địa chỉ, ngày sinh và giới tính của tài khoản hiện tại.",
)
def update_my_profile(
    request: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    return service.update_profile(current_user, request)


@router.post(
    "/avatar",
    response_model=AvatarUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Tải lên ảnh đại diện",
    description="Tải lên và cập nhật ảnh đại diện cá nhân (chấp nhận .jpg, .jpeg, .png, .webp, tối đa 5MB).",
)
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    return service.upload_avatar(current_user, file)
