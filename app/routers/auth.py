from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.role import Role
from app.models.user import User
from app.models.session import UserSession
from app.models.password_reset import PasswordResetToken
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest
)
from app.core.security import (
    SECRET_KEY,
    ALGORITHM,
    verify_password,
    hash_password,
    validate_password,
    create_access_token,
    create_refresh_token,
    create_password_reset_token
)
from app.core.auth import get_current_user
from app.core.email import send_reset_password_email


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Email hoặc mật khẩu không đúng"
        )

    u_id = getattr(user, "user_id", None) or getattr(user, "id", None)

    # 1. Kiểm tra khóa tài khoản vĩnh viễn
    if getattr(user, "is_locked", False):
        lock_reason = getattr(user, "lock_reason", "Không có lý do")
        raise HTTPException(
            status_code=423,
            detail=f"Tài khoản đã bị khóa. Lý do: {lock_reason}"
        )

    now = datetime.now()
    locked_until = getattr(user, "locked_until", None)

    # 2. Khóa tạm thời do nhập sai nhiều lần
    if locked_until is not None and locked_until > now:
        raise HTTPException(
            status_code=423,
            detail="Tài khoản tạm thời bị khóa. Vui lòng thử lại sau."
        )

    if locked_until is not None and locked_until <= now:
        user.locked_until = None
        user.failed_login_attempts = 0
        db.commit()

    # 3. Kiểm tra mật khẩu
    stored_password = getattr(user, "password", None) or getattr(user, "password_hash", None)
    if not stored_password or not verify_password(data.password, stored_password):
        failed_attempts = getattr(user, "failed_login_attempts", 0) + 1
        user.failed_login_attempts = failed_attempts

        if failed_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            db.commit()
            raise HTTPException(
                status_code=423,
                detail="Tài khoản tạm thời bị khóa trong 15 phút."
            )

        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Email hoặc mật khẩu không đúng"
        )

    # Đăng nhập đúng -> Reset trạng thái thất bại
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    # 4. Lấy Role
    role = db.query(Role).filter(
        Role.role_id == user.role_id
    ).first() if hasattr(user, "role_id") else None

    role_name = role.role_name if role else "STUDENT"

    # 5. Tạo Token
    access_token = create_access_token(user_id=u_id, role=role_name)
    refresh_token = create_refresh_token(user_id=u_id)

    # 6. Lưu Session
    try:
        session = UserSession(
            user_id=u_id,
            refresh_token=refresh_token,
            expires_at=datetime.now() + timedelta(days=7),
            revoked=False
        )
        db.add(session)
        db.commit()
    except Exception:
        db.rollback()

    return {
        "message": "Đăng nhập thành công",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": u_id,
            "full_name": getattr(user, "full_name", ""),
            "email": user.email,
            "role": role_name
        }
    }

@router.post("/refresh")
def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    session = db.query(UserSession).filter(
        UserSession.refresh_token == data.refresh_token
    ).first()

    if session is None or session.revoked:
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập không hợp lệ hoặc đã đăng xuất"
        )

    if session.expires_at <= datetime.now():
        session.revoked = True
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập đã hết hạn"
        )

    try:
        payload = jwt.decode(
            data.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        session.revoked = True
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập đã hết hạn"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Refresh token không hợp lệ"
        )

    user = db.query(User).filter(
        User.user_id == session.user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Người dùng không tồn tại"
        )

    if getattr(user, "is_locked", False):
        session.revoked = True
        db.commit()
        raise HTTPException(
            status_code=423,
            detail="Tài khoản đã bị khóa"
        )

    role = db.query(Role).filter(
        Role.role_id == user.role_id
    ).first() if hasattr(user, "role_id") else None

    role_name = role.role_name if role else "STUDENT"

    try:
        new_access_token = create_access_token(user_id=user.user_id, role=role_name)
    except TypeError:
        new_access_token = create_access_token(data={"sub": str(user.user_id), "role": role_name})

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    session = db.query(UserSession).filter(
        UserSession.refresh_token == data.refresh_token
    ).first()

    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập không hợp lệ"
        )

    session.revoked = True
    db.commit()

    return {
        "message": "Đăng xuất thành công"
    }