from datetime import datetime, timezone
from typing import List, Set
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.role import user_roles


def get_utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(String(1000), nullable=True)
    address = Column(String(255), nullable=True)
    date_of_birth = Column(String(50), nullable=True)
    gender = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    lock_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Quan hệ nhiều-nhiều với Role
    roles = relationship("Role", secondary=user_roles, lazy="joined")

    @property
    def role_names(self) -> List[str]:
        return [r.name for r in self.roles] if self.roles else []

    @property
    def permission_codes(self) -> List[str]:
        perms: Set[str] = set()
        if self.roles:
            for r in self.roles:
                if r.permissions:
                    for p in r.permissions:
                        perms.add(p.code)
        return sorted(list(perms))

    def has_role(self, role_name: str) -> bool:
        if not self.roles:
            return False
        normalized = role_name.strip().upper()
        return any(r.name.upper() == normalized for r in self.roles)

    def has_permission(self, permission_code: str) -> bool:
        # Quản trị viên (ADMIN) có tất cả các quyền
        if self.has_role("ADMIN"):
            return True
        return permission_code in self.permission_codes
