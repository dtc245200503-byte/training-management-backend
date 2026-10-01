from fastapi import APIRouter, Depends

from app.core.permissions import require_permission
from app.models.user import User


router = APIRouter(
    prefix="/api/rbac",
    tags=["RBAC"]
)


@router.get("/admin")
def admin_permission_test(
    current_user: User = Depends(
        require_permission("ROLE_MANAGE")
    )
):
    return {
        "message": "Bạn có quyền quản lý vai trò",
        "user_id": current_user.user_id
    }


@router.get("/grades")
def grade_permission_test(
    current_user: User = Depends(
        require_permission("GRADE_EDIT")
    )
):
    return {
        "message": "Bạn có quyền cập nhật điểm",
        "user_id": current_user.user_id
    }


@router.get("/tuition")
def tuition_permission_test(
    current_user: User = Depends(
        require_permission("TUITION_EDIT")
    )
):
    return {
        "message": "Bạn có quyền cập nhật học phí",
        "user_id": current_user.user_id
    }