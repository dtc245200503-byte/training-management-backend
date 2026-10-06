import pytest
from app.security.jwt import decode_token
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
