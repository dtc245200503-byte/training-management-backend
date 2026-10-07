from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.password_reset_token import PasswordResetToken


class PasswordResetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, token_hash: str, expires_at: datetime) -> PasswordResetToken:
        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False,
        )
        self.db.add(reset_token)
        self.db.commit()
        self.db.refresh(reset_token)
        return reset_token

    def get_by_token_hash(self, token_hash: str) -> Optional[PasswordResetToken]:
        return self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash
        ).first()

    def mark_used(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        reset_token.is_used = True
        reset_token.used_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(reset_token)
        return reset_token

    def invalidate_all_for_user(self, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        count = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.is_used == False,
        ).update(
            {"is_used": True, "used_at": now},
            synchronize_session="fetch",
        )
        self.db.commit()
        return count
