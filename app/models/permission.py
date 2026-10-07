from sqlalchemy import Column, Integer, String

from app.database import Base


class Permission(Base):
    __tablename__ = "permissions"

    permission_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    permission_name = Column(
        String(100),
        unique=True,
        nullable=False
    )

    description = Column(
        String(255),
        nullable=True
    )