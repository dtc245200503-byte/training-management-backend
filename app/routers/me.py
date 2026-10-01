from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole


router = APIRouter(
    prefix="/api",
    tags=["Current User"]
)


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roles = (
        db.query(Role)
        .join(
            UserRole,
            Role.role_id == UserRole.role_id
        )
        .filter(
            UserRole.user_id == current_user.user_id
        )
        .all()
    )

    permissions = (
        db.query(Permission)
        .join(
            RolePermission,
            Permission.permission_id
            == RolePermission.permission_id
        )
        .join(
            UserRole,
            RolePermission.role_id
            == UserRole.role_id
        )
        .filter(
            UserRole.user_id == current_user.user_id
        )
        .distinct()
        .all()
    )

    return {
        "user_id": current_user.user_id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "roles": [
            role.role_name
            for role in roles
        ],
        "permissions": [
            permission.permission_name
            for permission in permissions
        ]
    }