from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        return self.db.query(RefreshToken).filter(RefreshToken.token == token.strip()).first()

    def create(self, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token.strip(),
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)
        return refresh_token

    def revoke(self, refresh_token: RefreshToken) -> RefreshToken:
        refresh_token.is_revoked = True
        refresh_token.revoked_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(refresh_token)
        return refresh_token

    def revoke_by_token(self, token: str) -> Optional[RefreshToken]:
        db_token = self.get_by_token(token)
        if db_token:
            return self.revoke(db_token)
        return None

    def revoke_all_for_user(self, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        count = self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
        ).update(
            {"is_revoked": True, "revoked_at": now},
            synchronize_session="fetch",
        )
        self.db.commit()
        return count
