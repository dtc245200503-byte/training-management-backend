from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.role import Role, user_roles
from app.models.user import User


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Role]:
        return self.db.query(Role).all()

    def get_by_id(self, role_id: int) -> Optional[Role]:
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_by_name(self, name: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.name == name.strip().upper()).first()

    def get_by_names(self, names: List[str]) -> List[Role]:
        normalized = [n.strip().upper() for n in names]
        return self.db.query(Role).filter(Role.name.in_(normalized)).all()

    def create(self, role: Role) -> Role:
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def count_active_admins(self) -> int:
        """Đếm số lượng tài khoản quản trị viên (ADMIN) đang kích hoạt và không bị khóa."""
        return (
            self.db.query(User)
            .join(User.roles)
            .filter(
                Role.name == "ADMIN",
                User.is_active == True,
                User.is_locked == False,
            )
            .count()
        )
