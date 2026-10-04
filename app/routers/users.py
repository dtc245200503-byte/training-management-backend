import io
import pandas as pd

import secrets
import string

# 1. Thêm status, File, UploadFile vào import của fastapi
from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.email import send_new_account_email
from app.core.permissions import require_permission
from app.core.security import hash_password
from app.database import get_db
from app.models.role import Role
from app.models.session import UserSession
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import (
    CreateUserRequest,
    LockUserRequest,
    UpdateUserRequest
)


router = APIRouter(
    prefix="/api/users",
    tags=["User Management"]
)


def generate_temporary_password() -> str:
    alphabet = (
        string.ascii_letters
        + string.digits
    )

    return "".join(
        secrets.choice(alphabet)
        for _ in range(12)
    )


@router.post("")
async def create_user(
    data: CreateUserRequest,
    current_user: User = Depends(
        require_permission("USER_MANAGE")
    ),
    db: Session = Depends(get_db)
):
    existing_email = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email đã tồn tại trong hệ thống"
        )

    existing_username = db.query(User).filter(
        User.username == data.username
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Tên đăng nhập đã tồn tại"
        )

    role = db.query(Role).filter(
        Role.role_id == data.role_id
    ).first()

    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Vai trò không tồn tại"
        )

    temporary_password = (
        generate_temporary_password()
    )

    user = User(
        username=data.username,
        password=hash_password(
            temporary_password
        ),
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        role_id=data.role_id,
        failed_login_attempts=0,
        is_locked=False,
        lock_reason=None
    )

    db.add(user)
    db.flush()

    user_role = UserRole(
        user_id=user.user_id,
        role_id=data.role_id
    )

    db.add(user_role)
    db.commit()
    db.refresh(user)

    await send_new_account_email(
        email=user.email,
        full_name=user.full_name,
        temporary_password=temporary_password
    )

    return {
        "message": "Tạo tài khoản thành công",
        "user_id": user.user_id,
        "email": user.email,
        "role": role.role_name
    }


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: UpdateUserRequest,
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

    if data.email is not None:
        duplicate_email = db.query(User).filter(
            User.email == data.email,
            User.user_id != user_id
        ).first()

        if duplicate_email:
            raise HTTPException(
                status_code=400,
                detail="Email đã tồn tại trong hệ thống"
            )

        user.email = data.email

    if data.full_name is not None:
        user.full_name = data.full_name

    if data.phone is not None:
        user.phone = data.phone

    db.commit()

    return {
        "message": "Cập nhật tài khoản thành công",
        "user_id": user.user_id
    }


@router.put("/{user_id}/lock")
def lock_user(
    user_id: int,
    data: LockUserRequest,
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

    if current_user.user_id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Bạn không thể tự khóa tài khoản của chính mình"
        )

    lock_reason = data.lock_reason.strip()

    if not lock_reason:
        raise HTTPException(
            status_code=400,
            detail="Bắt buộc nhập lý do khóa tài khoản"
        )

    if user.is_locked:
        raise HTTPException(
            status_code=400,
            detail="Tài khoản đã bị khóa"
        )

    assigned_classes = db.execute(
        text(
            """
            SELECT
                class_id,
                class_name
            FROM classes
            WHERE instructor_id = :user_id
            ORDER BY class_id ASC
            """
        ),
        {
            "user_id": user_id
        }
    ).mappings().all()

    user.is_locked = True
    user.lock_reason = lock_reason

    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked == False
    ).update(
        {
            UserSession.revoked: True
        },
        synchronize_session=False
    )

    db.commit()

    classes_need_handover = [
        {
            "class_id": item["class_id"],
            "class_name": item["class_name"]
        }
        for item in assigned_classes
    ]

    return {
        "message": "Khóa tài khoản thành công",
        "user_id": user.user_id,
        "lock_reason": user.lock_reason,
        "classes_need_handover": classes_need_handover,
        "warning": (
            "Người dùng đang phụ trách lớp học. "
            "Cần thực hiện bàn giao."
            if classes_need_handover
            else None
        )
    }


@router.put("/{user_id}/unlock")
def unlock_user(
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

    if not user.is_locked:
        raise HTTPException(
            status_code=400,
            detail="Tài khoản hiện không bị khóa"
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


@router.get("")
def get_users(
    search: str | None = Query(
        default=None
    ),
    role_id: int | None = Query(
        default=None
    ),
    status: str | None = Query(
        default=None
    ),
    page: int = Query(
        default=1,
        ge=1
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100
    ),
    current_user: User = Depends(
        require_permission("USER_MANAGE")
    ),
    db: Session = Depends(get_db)
):
    query = db.query(User)

    if search:
        keyword = f"%{search}%"

        query = query.filter(
            or_(
                User.full_name.like(keyword),
                User.email.like(keyword),
                User.phone.like(keyword)
            )
        )

    if role_id is not None:
        query = query.join(
            UserRole,
            User.user_id == UserRole.user_id
        ).filter(
            UserRole.role_id == role_id
        )

    if status == "locked":
        query = query.filter(
            User.is_locked == True
        )

    elif status == "active":
        query = query.filter(
            User.is_locked == False
        )

    total = query.count()

    users = (
        query
        .order_by(User.user_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    user_ids = [
        user.user_id
        for user in users
    ]

    role_rows = []

    if user_ids:
        role_rows = (
            db.query(
                UserRole.user_id,
                Role.role_id,
                Role.role_name
            )
            .join(
                Role,
                UserRole.role_id == Role.role_id
            )
            .filter(
                UserRole.user_id.in_(user_ids)
            )
            .order_by(
                UserRole.user_id.asc(),
                Role.role_id.asc()
            )
            .all()
        )

    roles_by_user = {}

    for row in role_rows:
        if row.user_id not in roles_by_user:
            roles_by_user[row.user_id] = []

        roles_by_user[row.user_id].append(
            {
                "role_id": row.role_id,
                "role_name": row.role_name
            }
        )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [
            {
                "user_id": user.user_id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "role_id": user.role_id,
                "roles": roles_by_user.get(
                    user.user_id,
                    []
                ),
                "status": (
                    "locked"
                    if user.is_locked
                    else "active"
                ),
                "lock_reason": user.lock_reason
            }
            for user in users
        ]
    }


@router.post("/import-excel", status_code=status.HTTP_200_OK)
async def import_users_from_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(
        require_permission("USER_MANAGE")
    ),
    db: Session = Depends(get_db)
):
    # 1. Kiểm tra định dạng file upload
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File không đúng định dạng Excel (.xlsx, .xls)"
        )

    # 2. Đọc file Excel bằng Pandas
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Không thể đọc nội dung file Excel"
        )

    # Kiểm tra các cột bắt buộc trong file
    required_columns = ["HoTen", "Email", "SoDienThoai", "VaiTro"]
    for col in required_columns:
        if col not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Thiếu cột bắt buộc: {col} trong file Excel"
            )

    success_count = 0
    errors = []
    # Đổi get_password_hash -> hash_password cho khớp với import ở đầu file
    default_password_hash = hash_password("12345678")

    # 3. Duyệt từng dòng để lưu vào DB
    for index, row in df.iterrows():
        line_num = index + 2  # Dòng thực tế trong file Excel (tính cả Header)
        email = str(row["Email"]).strip() if pd.notna(row["Email"]) else ""
        full_name = str(row["HoTen"]).strip() if pd.notna(row["HoTen"]) else ""
        phone = str(row["SoDienThoai"]).strip() if pd.notna(row["SoDienThoai"]) else ""

        if not email or not full_name:
            errors.append(f"Dòng {line_num}: Thiếu Họ tên hoặc Email")
            continue

        # Kiểm tra trùng email
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            errors.append(f"Dòng {line_num}: Email '{email}' đã tồn tại")
            continue

        # Tự sinh username từ email
        username = email.split("@")[0]

        # Kiểm tra trùng username
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            username = f"{username}_{secrets.randbelow(1000)}"

        # Tạo người dùng mới (dùng thuộc tính password, is_locked chuẩn với model User)
        new_user = User(
            username=username,
            full_name=full_name,
            email=email,
            phone=phone,
            password=default_password_hash,
            is_locked=False,
            failed_login_attempts=0
        )
        db.add(new_user)
        success_count += 1

    db.commit()

    return {
        "message": "Import dữ liệu hoàn tất",
        "total_rows": len(df),
        "success_count": success_count,
        "failed_count": len(errors),
        "errors": errors
    }