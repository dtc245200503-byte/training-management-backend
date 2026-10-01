from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    refresh_token = Column(
        String(500),
        unique=True,
        nullable=False
    )

    expires_at = Column(
        DateTime,
        nullable=False
    )

    revoked = Column(
        Boolean,
        nullable=False,
        default=False
    )

    created_at = Column(
        DateTime,
        nullable=True
    )