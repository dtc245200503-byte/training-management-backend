from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.auth import MenuResponse
from app.security.dependencies import get_current_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/menu", tags=["Menu"])


@router.get(
    "",
    response_model=MenuResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách menu phân quyền",
    description="Trả về danh sách các menu và mục điều hướng phù hợp với quyền hạn của tài khoản.",
)
def get_user_menu(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    return service.get_menu_for_user(current_user)
