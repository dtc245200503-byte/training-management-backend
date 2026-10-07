from typing import List, Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.role import Role
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.strip().lower()).first()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_locked: Optional[bool] = None,
        role: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        query = self.db.query(User)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern),
                )
            )

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if is_locked is not None:
            query = query.filter(User.is_locked == is_locked)

        if role:
            query = query.join(User.roles).filter(Role.name == role.strip().upper())

        total = query.count()
        items = query.order_by(User.id.desc()).offset(skip).limit(limit).all()
        return items, total
