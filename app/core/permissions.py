from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole


def user_has_permission(
    user_id: int,
    permission_name: str,
    db: Session
) -> bool:

    permission = (
        db.query(Permission)
        .join(
            RolePermission,
            Permission.permission_id == RolePermission.permission_id
        )
        .join(
            UserRole,
            RolePermission.role_id == UserRole.role_id
        )
        .filter(
            UserRole.user_id == user_id,
            Permission.permission_name == permission_name
        )
        .first()
    )

    return permission is not None


def require_permission(permission_name: str):

    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        allowed = user_has_permission(
            current_user.user_id,
            permission_name,
            db
        )

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền thực hiện chức năng này"
            )

        return current_user

    return permission_checker