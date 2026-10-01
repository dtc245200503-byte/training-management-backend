from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import require_permission
from app.database import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.role import AssignRoleRequest, RemoveRoleRequest


router = APIRouter(
    prefix="/api/users",
    tags=["User Roles"]
)


@router.get("/{user_id}/roles")
def get_user_roles(
    user_id: int,
    current_user: User = Depends(
        require_permission("ROLE_MANAGE")
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

    roles = (
        db.query(Role)
        .join(
            UserRole,
            Role.role_id == UserRole.role_id
        )
        .filter(
            UserRole.user_id == user_id
        )
        .all()
    )

    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "roles": [
            {
                "role_id": role.role_id,
                "role_name": role.role_name
            }
            for role in roles
        ]
    }


@router.post("/{user_id}/roles")
def assign_role(
    user_id: int,
    data: AssignRoleRequest,
    current_user: User = Depends(
        require_permission("ROLE_MANAGE")
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

    role = db.query(Role).filter(
        Role.role_id == data.role_id
    ).first()

    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Vai trò không tồn tại"
        )

    existing_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == data.role_id
    ).first()

    if existing_role is not None:
        raise HTTPException(
            status_code=400,
            detail="Người dùng đã có vai trò này"
        )

    user_role = UserRole(
        user_id=user_id,
        role_id=data.role_id
    )

    db.add(user_role)
    db.commit()

    return {
        "message": "Gán vai trò thành công",
        "user_id": user_id,
        "role": role.role_name
    }


@router.delete("/{user_id}/roles")
def remove_role(
    user_id: int,
    data: RemoveRoleRequest,
    current_user: User = Depends(
        require_permission("ROLE_MANAGE")
    ),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(
        Role.role_id == data.role_id
    ).first()

    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Vai trò không tồn tại"
        )

    if (
        current_user.user_id == user_id
        and role.role_name == "ADMIN"
    ):
        raise HTTPException(
            status_code=400,
            detail="Bạn không thể tự thu hồi vai trò quản trị của chính mình"
        )

    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == data.role_id
    ).first()

    if user_role is None:
        raise HTTPException(
            status_code=404,
            detail="Người dùng không có vai trò này"
        )

    db.delete(user_role)
    db.commit()

    return {
        "message": "Thu hồi vai trò thành công"
    }