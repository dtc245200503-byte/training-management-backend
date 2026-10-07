from datetime import timedelta
import pytest
from app.security.jwt import create_access_token


class TestUnauthorizedNotificationS1_07:
    def test_unauthenticated_request_notification(self, client):
        """Test thông báo chưa xác thực: 401 Unauthorized kèm header WWW-Authenticate và thông điệp chuẩn xác."""
        response = client.get("/api/users")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["detail"] == "Chưa xác thực hoặc phiên đăng nhập đã hết hạn."

    def test_invalid_token_notification(self, client):
        """Test thông báo token không hợp lệ: 401 Unauthorized."""
        response = client.get(
            "/api/users",
            headers={"Authorization": "Bearer not-a-valid-token-format"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Token không hợp lệ."

    def test_expired_token_notification(self, client, admin_user):
        """Test thông báo phiên đăng nhập hết hạn: 401 Unauthorized."""
        expired_token = create_access_token(
            {"sub": str(admin_user.id), "email": admin_user.email},
            expires_delta=timedelta(seconds=-10),
        )
        response = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Phiên đăng nhập đã hết hạn."

    def test_forbidden_permission_notification(self, client, trainee_auth_headers):
        """Test thông báo từ chối quyền truy cập: 403 Forbidden với thông điệp rõ ràng."""
        response = client.post(
            "/api/users",
            headers=trainee_auth_headers,
            json={
                "email": "newbie@example.com",
                "password": "password123",
                "full_name": "Newbie",
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Bạn không có quyền thực hiện hành động này."

    def test_locked_account_access_notification(self, client, locked_auth_headers):
        """Test thông báo tài khoản bị khóa khi cố gắng sử dụng API: 403 Forbidden."""
        response = client.get("/api/menu", headers=locked_auth_headers)
        assert response.status_code == 403
        assert "Tài khoản của bạn đã bị khóa" in response.json()["detail"]
