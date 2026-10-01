from sqlalchemy import Column, ForeignKey, Integer

from app.database import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(
        Integer,
        ForeignKey("roles.role_id"),
        primary_key=True
    )

    permission_id = Column(
        Integer,
        ForeignKey("permissions.permission_id"),
        primary_key=True
    )