from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.avatar import MAX_AVATAR_BYTES, prepare_avatar
from app.database import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.profile import ProfileResponse, UpdateProfileRequest


router = APIRouter(
    prefix="/api",
    tags=["Current User"]
)


@router.get("/me", response_model=ProfileResponse)
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
        "phone": current_user.phone,
        "date_of_birth": current_user.date_of_birth,
        "address": current_user.address,
        "avatar_url": current_user.avatar_url,
        "avatar_thumbnail_url": current_user.avatar_thumbnail_url,
        "roles": [
            role.role_name
            for role in roles
        ],
        "permissions": [
            permission.permission_name
            for permission in permissions
        ]
    }


@router.put("/me", response_model=ProfileResponse)
def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # The schema forbids every field outside the four editable profile fields.
    # Identity always comes from the authenticated user, never the request.
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return get_me(current_user=current_user, db=db)


@router.put("/me/avatar", response_model=ProfileResponse)
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read(MAX_AVATAR_BYTES + 1)
        avatar_url, thumbnail_url = prepare_avatar(content, file.content_type)
    finally:
        await file.close()
    current_user.avatar_url = avatar_url
    current_user.avatar_thumbnail_url = thumbnail_url
    db.commit()
    db.refresh(current_user)
    return get_me(current_user=current_user, db=db)


@router.delete("/me/avatar", response_model=ProfileResponse)
def remove_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.avatar_url = None
    current_user.avatar_thumbnail_url = None
    db.commit()
    db.refresh(current_user)
    return get_me(current_user=current_user, db=db)
