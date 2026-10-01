from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String(50),
        unique=True,
        nullable=False
    )

    password = Column(
        String(255),
        nullable=False
    )

    full_name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(100),
        unique=True,
        nullable=False
    )

    phone = Column(
        String(20),
        nullable=True
    )

    role_id = Column(
        Integer,
        ForeignKey("roles.role_id"),
        nullable=True
    )

    failed_login_attempts = Column(
        Integer,
        nullable=False,
        default=0
    )

    locked_until = Column(
        DateTime,
        nullable=True
    )

    is_locked = Column(
        Boolean,
        nullable=False,
        default=False
    )

    lock_reason = Column(
        String(255),
        nullable=True
    )