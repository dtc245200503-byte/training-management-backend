import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash


load_dotenv()

password_hash = PasswordHash.recommended()

# Dùng chuỗi mặc định an toàn nếu os.getenv("SECRET_KEY") trả về None hoặc rỗng
SECRET_KEY = os.getenv("SECRET_KEY") or "fallback_secret_key_training_management_system_2026"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password
    )


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False

    if re.search(r"[A-Za-z]", password) is None:
        return False

    if re.search(r"[0-9]", password) is None:
        return False

    return True


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire
    }

    return jwt.encode(
        payload,
        str(SECRET_KEY),
        algorithm=ALGORITHM
    )


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire
    }

    return jwt.encode(
        payload,
        str(SECRET_KEY),
        algorithm=ALGORITHM
    )


def create_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            str(SECRET_KEY),
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != "access":
            return None

        return payload

    except jwt.InvalidTokenError:
        return None