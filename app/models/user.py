from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text

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

    date_of_birth = Column(Date, nullable=True)
    address = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    avatar_thumbnail_url = Column(Text, nullable=True)

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
