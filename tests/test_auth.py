from datetime import timedelta
import pytest
from app.models.refresh_token import RefreshToken
from app.security.jwt import create_refresh_token, decode_token
from app.security.password import hash_password, verify_password



class TestLoginS1_01:
    def test_login_success(self, client, test_user):
        """Test đăng nhập thành công với email và mật khẩu đúng."""
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Đăng nhập thành công"
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "user@example.com"
        assert data["user"]["id"] == test_user.id
        assert data["user"]["is_active"] is True

        # Bảo mật: Tuyệt đối không trả về password hay password_hash
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]
        assert "password" not in data
        assert "password_hash" not in data

    def test_login_token_validity(self, client, test_user):
        """Test JWT token trả về chứa thông tin định danh và expiration hợp lệ."""
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()

        # Kiểm tra access token
        access_payload = decode_token(data["access_token"])
        assert access_payload["sub"] == str(test_user.id)
        assert access_payload["email"] == "user@example.com"
        assert access_payload["type"] == "access"
        assert "exp" in access_payload
        assert "iat" in access_payload

        # Kiểm tra refresh token
        refresh_payload = decode_token(data["refresh_token"])
        assert refresh_payload["sub"] == str(test_user.id)
        assert refresh_payload["email"] == "user@example.com"
        assert refresh_payload["type"] == "refresh"
        assert "exp" in refresh_payload

    def test_login_wrong_password(self, client, test_user):
        """Test đăng nhập với mật khẩu sai trả về 401 Unauthorized."""
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Email hoặc mật khẩu không chính xác."

    def test_login_nonexistent_email(self, client, test_user):
        """Test đăng nhập với email không tồn tại trả về 401 và thông báo chung (chống account enumeration)."""
        response = client.post(
            "/api/auth/login",
            json={"email": "notfound@example.com", "password": "password123"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Email hoặc mật khẩu không chính xác."

    def test_login_missing_email(self, client):
        """Test thiếu trường email trả về 422 Unprocessable Entity."""
        response = client.post(
            "/api/auth/login",
            json={"password": "password123"},
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client):
        """Test thiếu trường password trả về 422 Unprocessable Entity."""
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 422

    def test_login_invalid_email_format(self, client):
        """Test email không đúng định dạng trả về 422 Unprocessable Entity."""
        response = client.post(
            "/api/auth/login",
            json={"email": "invalid-email-format", "password": "password123"},
        )
        assert response.status_code == 422

    def test_login_inactive_user(self, client, inactive_user):
        """Test tài khoản bị vô hiệu hóa không được đăng nhập."""
        response = client.post(
            "/api/auth/login",
            json={"email": "inactive@example.com", "password": "password123"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Tài khoản đã bị vô hiệu hóa."

    def test_password_hash_and_verification(self):
        """Test cơ chế mã hóa bcrypt và xác thực mật khẩu."""
        raw_password = "MySecureP@ssw0rd!"
        hashed = hash_password(raw_password)

        # Hash không được trùng với mật khẩu gốc
        assert hashed != raw_password
        # Hash phải verify thành công với mật khẩu đúng
        assert verify_password(raw_password, hashed) is True
        # Hash phải verify thất bại với mật khẩu sai
        assert verify_password("WrongP@ssw0rd", hashed) is False


class TestSessionAndLogoutS1_02:
    def test_login_persists_refresh_token(self, client, test_user, db_session):
        """Test đăng nhập thành công lưu refresh token vào database (session persistence)."""
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        refresh_token_str = data["refresh_token"]

        # Kiểm tra token được lưu trong bảng refresh_tokens
        db_token = db_session.query(RefreshToken).filter(RefreshToken.token == refresh_token_str).first()
        assert db_token is not None
        assert db_token.user_id == test_user.id
        assert db_token.is_revoked is False
        assert db_token.revoked_at is None

    def test_refresh_token_success(self, client, test_user):
        """Test refresh token hợp lệ trả về access token mới thành công."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        refresh_token = login_resp.json()["refresh_token"]
        old_access_token = login_resp.json()["access_token"]

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["message"] == "Làm mới token thành công"
        assert "access_token" in data
        assert data["refresh_token"] == refresh_token
        assert data["token_type"] == "bearer"

        # Access token mới giải mã hợp lệ
        new_payload = decode_token(data["access_token"])
        assert new_payload["sub"] == str(test_user.id)
        assert new_payload["email"] == "user@example.com"
        assert new_payload["type"] == "access"

        # Không để lộ thông tin nhạy cảm
        assert "password" not in data
        assert "password_hash" not in data

    def test_multiple_refreshes_session_persistence(self, client, test_user):
        """Test có thể refresh nhiều lần trong cùng một phiên làm việc hợp lệ."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Lần refresh 1
        resp1 = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert resp1.status_code == 200
        token1 = resp1.json()["access_token"]

        # Lần refresh 2
        resp2 = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert resp2.status_code == 200
        token2 = resp2.json()["access_token"]

        assert token1 != ""
        assert token2 != ""

    def test_logout_success_and_revokes_token(self, client, test_user, db_session):
        """Test đăng xuất thành công và refresh token bị thu hồi trong database."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        logout_resp = client.post(
            "/api/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert logout_resp.status_code == 200
        data = logout_resp.json()
        assert data["message"] == "Đăng xuất thành công"

        # Kiểm tra token đã bị thu hồi trong database
        db_token = db_session.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        assert db_token is not None
        assert db_token.is_revoked is True
        assert db_token.revoked_at is not None

    def test_refresh_with_revoked_token_rejected(self, client, test_user):
        """Test từ chối cấp access token mới khi refresh token đã bị thu hồi (sau logout)."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Logout để thu hồi token
        logout_resp = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
        assert logout_resp.status_code == 200

        # Thử refresh với token đã thu hồi
        refresh_resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_resp.status_code == 401
        assert refresh_resp.json()["detail"] == "Refresh token đã bị thu hồi."

    def test_logout_with_already_revoked_token_rejected(self, client, test_user):
        """Test từ chối đăng xuất lại khi refresh token đã bị thu hồi trước đó."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Logout lần 1 thành công
        resp1 = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
        assert resp1.status_code == 200

        # Logout lần 2 thất bại vì token đã revoke
        resp2 = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
        assert resp2.status_code == 401
        assert resp2.json()["detail"] == "Refresh token đã bị thu hồi."

    def test_refresh_with_invalid_token_rejected(self, client):
        """Test từ chối token không đúng định dạng JWT."""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.string"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token không hợp lệ."

    def test_logout_with_invalid_token_rejected(self, client):
        """Test từ chối logout với token không đúng định dạng JWT."""
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": "not-a-valid-token"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token không hợp lệ."

    def test_refresh_with_expired_token_rejected(self, client, test_user):
        """Test từ chối token đã hết hạn khi refresh."""
        expired_token = create_refresh_token(
            {"sub": str(test_user.id), "email": test_user.email},
            expires_delta=timedelta(seconds=-10),
        )
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": expired_token},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token đã hết hạn."

    def test_logout_with_expired_token_rejected(self, client, test_user):
        """Test từ chối logout với token đã hết hạn."""
        expired_token = create_refresh_token(
            {"sub": str(test_user.id), "email": test_user.email},
            expires_delta=timedelta(seconds=-10),
        )
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": expired_token},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token đã hết hạn."

    def test_refresh_with_unregistered_token_rejected(self, client, test_user):
        """Test từ chối token hợp lệ về mặt JWT nhưng không tồn tại trong database."""
        unregistered_token = create_refresh_token(
            {"sub": str(test_user.id), "email": test_user.email}
        )
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": unregistered_token},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token không hợp lệ."

    def test_logout_with_unregistered_token_rejected(self, client, test_user):
        """Test từ chối logout với token không tồn tại trong database."""
        unregistered_token = create_refresh_token(
            {"sub": str(test_user.id), "email": test_user.email}
        )
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": unregistered_token},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token không hợp lệ."

    def test_refresh_with_access_token_rejected(self, client, test_user):
        """Test từ chối khi truyền access token vào endpoint refresh token."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        access_token = login_resp.json()["access_token"]

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token không hợp lệ."

    def test_logout_with_access_token_rejected(self, client, test_user):
        """Test từ chối khi truyền access token vào endpoint logout."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        access_token = login_resp.json()["access_token"]

        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Refresh token không hợp lệ."

    def test_refresh_inactive_user_rejected(self, client, test_user, db_session):
        """Test từ chối refresh token khi tài khoản người dùng đã bị vô hiệu hóa."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Vô hiệu hóa tài khoản người dùng
        test_user.is_active = False
        db_session.commit()

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Tài khoản không tồn tại hoặc đã bị vô hiệu hóa."

    def test_refresh_missing_field(self, client):
        """Test thiếu trường refresh_token trả về 422 Unprocessable Entity."""
        response = client.post("/api/auth/refresh", json={})
        assert response.status_code == 422

    def test_logout_missing_field(self, client):
        """Test thiếu trường refresh_token khi logout trả về 422 Unprocessable Entity."""
        response = client.post("/api/auth/logout", json={})
        assert response.status_code == 422

