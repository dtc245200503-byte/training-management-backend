from datetime import datetime, timedelta, timezone
import hashlib
import pytest
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.security.jwt import create_refresh_token
from app.services.email_service import EmailService


class TestForgotResetPasswordS1_03:
    def setup_method(self):
        EmailService.clear_outbox()

    def test_forgot_password_success_sends_email(self, client, test_user, db_session):
        """Test yêu cầu quên mật khẩu với email hợp lệ tạo token hash và gửi email."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": test_user.email},
        )
        assert response.status_code == 200
        data = response.json()
        assert "hướng dẫn đặt lại mật khẩu đã được gửi" in data["message"]

        # Token không được để lộ trong response (bảo mật)
        assert "token" not in data
        assert "reset_token" not in data

        # Kiểm tra token hash được lưu trong DB
        db_token = db_session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == test_user.id
        ).first()
        assert db_token is not None
        assert db_token.is_used is False
        expires_at = db_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at > datetime.now(timezone.utc)

        # Kiểm tra email outbox đã nhận được thư chứa raw token
        outbox = EmailService.get_outbox()
        assert len(outbox) == 1
        assert outbox[0]["to"] == test_user.email
        raw_token = outbox[0]["token"]
        assert raw_token is not None

        # Kiểm tra token_hash trong DB đúng là SHA-256 của raw_token
        expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        assert db_token.token_hash == expected_hash

    def test_forgot_password_nonexistent_email_anti_enumeration(self, client):
        """Test yêu cầu với email không tồn tại trả về cùng thông điệp chung (chống enumeration) và không gửi email."""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "hướng dẫn đặt lại mật khẩu đã được gửi" in data["message"]

        # Không gửi email nào
        assert len(EmailService.get_outbox()) == 0

    def test_forgot_password_inactive_or_locked_user(self, client, inactive_user, locked_user):
        """Test yêu cầu cho tài khoản bị vô hiệu hóa hoặc bị khóa không gửi email."""
        resp1 = client.post("/api/auth/forgot-password", json={"email": inactive_user.email})
        assert resp1.status_code == 200
        assert len(EmailService.get_outbox()) == 0

        resp2 = client.post("/api/auth/forgot-password", json={"email": locked_user.email})
        assert resp2.status_code == 200
        assert len(EmailService.get_outbox()) == 0

    def test_verify_reset_token_valid(self, client, test_user):
        """Test xác thực mã reset hợp lệ."""
        client.post("/api/auth/forgot-password", json={"email": test_user.email})
        raw_token = EmailService.get_last_token_for(test_user.email)

        response = client.post(
            "/api/auth/verify-reset-token",
            json={"token": raw_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["message"] == "Mã xác thực hợp lệ."

    def test_verify_reset_token_invalid(self, client):
        """Test xác thực mã reset không hợp lệ trả về 400."""
        response = client.post(
            "/api/auth/verify-reset-token",
            json={"token": "invalid-token-string"},
        )
        assert response.status_code == 400
        assert "không hợp lệ hoặc đã hết hạn" in response.json()["detail"]

    def test_verify_reset_token_expired(self, client, test_user, db_session):
        """Test xác thực mã reset đã hết hạn trả về 400."""
        raw_token = "expired_raw_token_xyz"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expired_token = PasswordResetToken(
            user_id=test_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            is_used=False,
        )
        db_session.add(expired_token)
        db_session.commit()

        response = client.post(
            "/api/auth/verify-reset-token",
            json={"token": raw_token},
        )
        assert response.status_code == 400
        assert "không hợp lệ hoặc đã hết hạn" in response.json()["detail"]

    def test_reset_password_success_and_login_with_new_password(self, client, test_user, db_session):
        """Test đặt lại mật khẩu thành công và đăng nhập bằng mật khẩu mới."""
        client.post("/api/auth/forgot-password", json={"email": test_user.email})
        raw_token = EmailService.get_last_token_for(test_user.email)

        new_password = "NewSecretPassword456!"
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": new_password,
                "confirm_password": new_password,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Đặt lại mật khẩu thành công" in data["message"]

        # Kiểm tra token đã được đánh dấu là used trong DB
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        db_token = db_session.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash
        ).first()
        assert db_token.is_used is True
        assert db_token.used_at is not None

        # Không thể đăng nhập bằng mật khẩu cũ
        old_login = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        assert old_login.status_code == 401

        # Đăng nhập thành công bằng mật khẩu mới
        new_login = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": new_password},
        )
        assert new_login.status_code == 200
        assert "access_token" in new_login.json()

    def test_reset_password_revokes_existing_sessions(self, client, test_user):
        """Test đặt lại mật khẩu hủy mọi refresh token / phiên làm việc hiện tại."""
        # Đăng nhập tạo phiên
        login_resp = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Yêu cầu và thực hiện reset password
        client.post("/api/auth/forgot-password", json={"email": test_user.email})
        raw_token = EmailService.get_last_token_for(test_user.email)

        client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "AnotherNewPassword789",
            },
        )

        # Refresh token cũ bị từ chối
        refresh_resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401
        assert refresh_resp.json()["detail"] == "Refresh token đã bị thu hồi."

    def test_reset_password_already_used_token_rejected(self, client, test_user):
        """Test không thể tái sử dụng token đã được dùng."""
        client.post("/api/auth/forgot-password", json={"email": test_user.email})
        raw_token = EmailService.get_last_token_for(test_user.email)

        # Lần reset 1 thành công
        resp1 = client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword111"},
        )
        assert resp1.status_code == 200

        # Lần reset 2 thất bại
        resp2 = client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword222"},
        )
        assert resp2.status_code == 400
        assert "không hợp lệ hoặc đã hết hạn" in resp2.json()["detail"]

    def test_reset_password_mismatched_confirm_password(self, client, test_user):
        """Test mật khẩu xác nhận không khớp trả về 400."""
        client.post("/api/auth/forgot-password", json={"email": test_user.email})
        raw_token = EmailService.get_last_token_for(test_user.email)

        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "Password1234",
                "confirm_password": "Password9999",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Mật khẩu xác nhận không khớp."

    def test_reset_password_too_short(self, client, test_user):
        """Test mật khẩu mới dưới 6 ký tự trả về 400 hoặc 422."""
        client.post("/api/auth/forgot-password", json={"email": test_user.email})
        raw_token = EmailService.get_last_token_for(test_user.email)

        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "123",
            },
        )
        assert response.status_code in (400, 422)
