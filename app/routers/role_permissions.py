from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.database import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.schemas.role import UpdateRolePermissionsRequest


router = APIRouter(
    prefix="/api/roles",
    tags=["Role Permissions"]
)


@router.get("/permissions")
def get_roles_permissions(
    current_user: User = Depends(
        require_permission("ROLE_MANAGE")
    ),
    db: Session = Depends(get_db)
):
    roles = (
        db.query(Role)
        .order_by(Role.role_id.asc())
        .all()
    )

    permissions = (
        db.query(Permission)
        .order_by(Permission.permission_id.asc())
        .all()
    )

    role_permissions = (
        db.query(RolePermission)
        .all()
    )

    permission_map = {}

    for item in role_permissions:
        if item.role_id not in permission_map:
            permission_map[item.role_id] = []

        permission_map[item.role_id].append(
            item.permission_id
        )

    return {
        "permissions": [
            {
                "permission_id": permission.permission_id,
                "permission_name": permission.permission_name,
                "description": permission.description
            }
            for permission in permissions
        ],
        "roles": [
            {
                "role_id": role.role_id,
                "role_name": role.role_name,
                "permission_ids": permission_map.get(
                    role.role_id,
                    []
                )
            }
            for role in roles
        ]
    }


@router.put("/{role_id}/permissions")
def update_role_permissions(
    role_id: int,
    data: UpdateRolePermissionsRequest,
    current_user: User = Depends(
        require_permission("ROLE_MANAGE")
    ),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(
        Role.role_id == role_id
    ).first()

    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Vai trò không tồn tại"
        )

    permission_ids = list(
        set(data.permission_ids)
    )

    if permission_ids:
        permissions = (
            db.query(Permission)
            .filter(
                Permission.permission_id.in_(
                    permission_ids
                )
            )
            .all()
        )

        if len(permissions) != len(permission_ids):
            raise HTTPException(
                status_code=400,
                detail="Danh sách quyền không hợp lệ"
            )

    if role.role_name == "ADMIN":
        all_permission_ids = {
            permission.permission_id
            for permission in db.query(Permission).all()
        }

        if set(permission_ids) != all_permission_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Không thể thu hồi quyền của "
                    "vai trò Quản trị viên"
                )
            )

    db.query(RolePermission).filter(
        RolePermission.role_id == role_id
    ).delete(
        synchronize_session=False
    )

    for permission_id in permission_ids:
        db.add(
            RolePermission(
                role_id=role_id,
                permission_id=permission_id
            )
        )

    db.commit()

    return {
        "message": "Cập nhật phân quyền thành công",
        "role_id": role_id,
        "permission_ids": permission_ids
    }