import hashlib
import hmac
import math
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.core.security import SECRET_KEY
from app.models.consultation import ConsultationChallenge, ConsultationLead, ConsultationRateBucket

CHALLENGE_TTL = 600
MIN_FILL_SECONDS = 2
MAX_ANSWER_ATTEMPTS = 3
SUBMIT_LIMIT = 5
CHALLENGE_LIMIT = 20
IP_WINDOW_SECONDS = 900
PHONE_WINDOW_SECONDS = 600


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fingerprint(value):
    return hmac.new(str(SECRET_KEY).encode(), value.encode(), hashlib.sha256).hexdigest()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def answer_hash(token_digest, answer):
    return fingerprint(f"answer:{token_digest}:{int(answer)}")


def initialize_bucket(db, key, now):
    # Initialization happens before acquiring challenge/lead transaction locks.
    if db.get(ConsultationRateBucket, key) is None:
        db.add(ConsultationRateBucket(key=key, window_start=now, count=0))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # Another worker initialized the same key.


def locked_bucket(db, key):
    return db.query(ConsultationRateBucket).filter_by(key=key).populate_existing().with_for_update().one()


def consume_ip_rate(db, client, action):
    now = utcnow()
    key = fingerprint(f"{action}:{client}")
    initialize_bucket(db, key, now)
    bucket = locked_bucket(db, key)
    if now >= bucket.window_start + timedelta(seconds=IP_WINDOW_SECONDS):
        bucket.window_start, bucket.count = now, 0
    limit = CHALLENGE_LIMIT if action == "challenge" else SUBMIT_LIMIT
    if bucket.count >= limit:
        retry = max(1, math.ceil((bucket.window_start + timedelta(seconds=IP_WINDOW_SECONDS) - now).total_seconds()))
        raise HTTPException(status_code=429, detail="Bạn đã gửi quá nhiều yêu cầu. Vui lòng chờ một lúc rồi thử lại.", headers={"Retry-After": str(retry)})
    bucket.count += 1
    db.commit()  # Count failed submissions too; limits survive restarts/workers.


def create_challenge(db, client):
    now = utcnow()
    # Remove old anti-spam records only; keep all leads and recent retry tokens.
    cutoff = now - timedelta(days=1)
    db.query(ConsultationChallenge).filter(ConsultationChallenge.expires_at < cutoff).delete(synchronize_session=False)
    db.query(ConsultationRateBucket).filter(ConsultationRateBucket.window_start < cutoff).delete(synchronize_session=False)
    left, right = secrets.randbelow(20) + 1, secrets.randbelow(20) + 1
    token = secrets.token_urlsafe(32)
    digest = token_hash(token)
    db.add(ConsultationChallenge(token_hash=digest, client_key=fingerprint(f"client:{client}"),
        answer_hash=answer_hash(digest, str(left + right)), issued_at=now,
        expires_at=now + timedelta(seconds=CHALLENGE_TTL), attempts=0))
    db.commit()
    return {"challenge_token": token, "question": f"{left} + {right} bằng bao nhiêu?",
            "expires_in": CHALLENGE_TTL, "min_wait_seconds": MIN_FILL_SECONDS}


def submit_consultation(db, client, data):
    if data.website:
        raise HTTPException(status_code=400, detail="Không thể xác minh yêu cầu. Vui lòng tải lại câu hỏi xác minh.")
    now = utcnow()
    phone_key = fingerprint(f"phone:{data.phone}")
    initialize_bucket(db, phone_key, now)
    digest = token_hash(data.challenge_token)
    challenge = db.query(ConsultationChallenge).filter_by(token_hash=digest).with_for_update().first()
    if (challenge is None or challenge.client_key != fingerprint(f"client:{client}")
            or challenge.expires_at <= now or challenge.attempts >= MAX_ANSWER_ATTEMPTS):
        raise HTTPException(status_code=400, detail="Câu hỏi xác minh đã hết hạn hoặc không hợp lệ. Vui lòng lấy câu hỏi mới.")
    if (now - challenge.issued_at).total_seconds() < MIN_FILL_SECONDS:
        raise HTTPException(status_code=400, detail="Vui lòng chờ ít giây trước khi gửi biểu mẫu.")
    if not hmac.compare_digest(challenge.answer_hash, answer_hash(digest, data.challenge_answer)):
        challenge.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Câu trả lời xác minh chưa đúng. Vui lòng kiểm tra hoặc lấy câu hỏi mới.")
    if challenge.lead_id is not None:
        # A network retry/double click with the same token cannot create another lead.
        lead = db.query(ConsultationLead).filter_by(lead_id=challenge.lead_id).with_for_update().first()
        if lead is not None and lead.phone == data.phone:
            return False
        raise HTTPException(status_code=409, detail="Biểu mẫu đã được gửi. Vui lòng lấy câu hỏi mới để gửi thông tin khác.")
    phone_bucket = locked_bucket(db, phone_key)
    if phone_bucket.count and now < phone_bucket.window_start + timedelta(seconds=PHONE_WINDOW_SECONDS):
        raise HTTPException(status_code=409, detail="Yêu cầu tư vấn cho số điện thoại này đã được ghi nhận gần đây. Vui lòng chờ trung tâm liên hệ.")
    phone_bucket.count, phone_bucket.window_start = 1, now
    lead = ConsultationLead(full_name=data.full_name, phone=data.phone, email=str(data.email) if data.email else None,
        interest=data.interest, message=data.message, status="new", created_at=now)
    db.add(lead); db.flush()
    challenge.lead_id = lead.lead_id
    db.commit()
    return True
