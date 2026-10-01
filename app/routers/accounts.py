from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.database import get_db
from app.models.session import UserSession
from app.models.user import User
from app.schemas.account import LockAccountRequest


router = APIRouter(
    prefix="/api/users",
    tags=["Account Management"]
)


@router.post("/{user_id}/lock")
def lock_account(
    user_id: int,
    data: LockAccountRequest,
    current_user: User = Depends(
        require_permission("USER_MANAGE")
    ),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.user_id == user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy người dùng"
        )

    if not data.reason.strip():
        raise HTTPException(
            status_code=400,
            detail="Bắt buộc nhập lý do khóa tài khoản"
        )

    if user.user_id == current_user.user_id:
        raise HTTPException(
            status_code=400,
            detail="Bạn không thể tự khóa tài khoản của chính mình"
        )

    user.is_locked = True
    user.lock_reason = data.reason.strip()

    db.query(UserSession).filter(
        UserSession.user_id == user.user_id,
        UserSession.revoked == False
    ).update(
        {
            UserSession.revoked: True
        },
        synchronize_session=False
    )

    classes = db.execute(
        text("""
            SELECT class_id, class_name
            FROM classes
            WHERE instructor_id = :user_id
        """),
        {
            "user_id": user.user_id
        }
    ).fetchall()

    db.commit()

    response = {
        "message": "Khóa tài khoản thành công",
        "user_id": user.user_id,
        "reason": user.lock_reason,
        "classes_need_handover": []
    }

    if classes:
        response["warning"] = (
            "Người dùng đang phụ trách lớp học. "
            "Cần thực hiện bàn giao."
        )

        response["classes_need_handover"] = [
            {
                "class_id": item.class_id,
                "class_name": item.class_name
            }
            for item in classes
        ]

    return response


@router.post("/{user_id}/unlock")
def unlock_account(
    user_id: int,
    current_user: User = Depends(
        require_permission("USER_MANAGE")
    ),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.user_id == user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy người dùng"
        )

    user.is_locked = False
    user.lock_reason = None
    user.failed_login_attempts = 0
    user.locked_until = None

    db.commit()

    return {
        "message": "Mở khóa tài khoản thành công",
        "user_id": user.user_id
    }