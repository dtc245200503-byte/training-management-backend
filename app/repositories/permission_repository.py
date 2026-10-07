from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.permission import Permission


class PermissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Permission]:
        return self.db.query(Permission).all()

    def get_by_id(self, permission_id: int) -> Optional[Permission]:
        return self.db.query(Permission).filter(Permission.id == permission_id).first()

    def get_by_code(self, code: str) -> Optional[Permission]:
        return self.db.query(Permission).filter(Permission.code == code.strip()).first()

    def create(self, permission: Permission) -> Permission:
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission
