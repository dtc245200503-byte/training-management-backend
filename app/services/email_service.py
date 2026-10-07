from typing import Any, Dict, List

# Hộp thư giả lập (in-memory outbox) để phục vụ gửi mail và kiểm thử tự động
_outbox: List[Dict[str, Any]] = []


class EmailService:
    @staticmethod
    def send_password_reset_email(to_email: str, token: str, reset_url: str = ""):
        """Gửi email chứa link / mã đặt lại mật khẩu."""
        message = {
            "to": to_email,
            "subject": "Khôi phục mật khẩu tài khoản TMS",
            "token": token,
            "reset_url": reset_url or f"/reset-password?token={token}",
        }
        _outbox.append(message)
        return message

    @staticmethod
    def get_outbox() -> List[Dict[str, Any]]:
        return _outbox

    @staticmethod
    def clear_outbox():
        _outbox.clear()

    @staticmethod
    def get_last_token_for(email: str) -> str | None:
        for mail in reversed(_outbox):
            if mail.get("to") == email:
                return mail.get("token")
        return None
