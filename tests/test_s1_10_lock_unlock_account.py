import pytest


class TestLockUnlockAccountS1_10:
    def test_lock_account_flow(self, client, admin_auth_headers, trainee_user):
        """Test quy trình khóa tài khoản: cập nhật trạng thái, lưu lý do và lập tức vô hiệu hóa phiên làm việc."""
        # Trainee đăng nhập lấy session trước
        login_resp = client.post(
            "/api/auth/login",
            json={"email": trainee_user.email, "password": "password123"},
        )
        assert login_resp.status_code == 200
        access_token = login_resp.json()["access_token"]
        refresh_token = login_resp.json()["refresh_token"]

        # Admin tiến hành khóa tài khoản
        lock_resp = client.post(
            f"/api/users/{trainee_user.id}/lock",
            headers=admin_auth_headers,
            json={"reason": "Vi phạm nghiêm trọng chính sách đào tạo"},
        )
        assert lock_resp.status_code == 200
        data = lock_resp.json()
        assert data["message"] == "Khóa tài khoản thành công."
        assert data["is_locked"] is True
        assert data["lock_reason"] == "Vi phạm nghiêm trọng chính sách đào tạo"
        assert data["locked_at"] is not None

        # 1. Trainee không thể tiếp tục gọi API bằng access token cũ
        api_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert api_resp.status_code == 403
        assert "Tài khoản của bạn đã bị khóa" in api_resp.json()["detail"]

        # 2. Refresh token của trainee đã bị thu hồi ngay khi bị khóa
        refresh_resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_resp.status_code == 401

        # 3. Trainee không thể đăng nhập lại
        login_again = client.post(
            "/api/auth/login",
            json={"email": trainee_user.email, "password": "password123"},
        )
        assert login_again.status_code == 403
        assert "Tài khoản của bạn đã bị khóa" in login_again.json()["detail"]

    def test_unlock_account_restores_access(self, client, admin_auth_headers, trainee_user):
        """Test mở khóa tài khoản cho phép người dùng đăng nhập và sử dụng hệ thống trở lại bình thường."""
        # Khóa tài khoản
        client.post(
            f"/api/users/{trainee_user.id}/lock",
            headers=admin_auth_headers,
            json={"reason": "Khóa tạm thời"},
        )

        # Mở khóa tài khoản
        unlock_resp = client.post(
            f"/api/users/{trainee_user.id}/unlock",
            headers=admin_auth_headers,
        )
        assert unlock_resp.status_code == 200
        data = unlock_resp.json()
        assert data["message"] == "Mở khóa tài khoản thành công."
        assert data["is_locked"] is False
        assert data["locked_at"] is None
        assert data["lock_reason"] is None

        # Người dùng đăng nhập lại thành công
        login_resp = client.post(
            "/api/auth/login",
            json={"email": trainee_user.email, "password": "password123"},
        )
        assert login_resp.status_code == 200
        new_token = login_resp.json()["access_token"]

        # Gọi API bảo vệ thành công
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["is_locked"] is False

    def test_admin_cannot_lock_self(self, client, admin_user, admin_auth_headers):
        """Test Admin không được phép tự khóa tài khoản của chính mình (400)."""
        response = client.post(
            f"/api/users/{admin_user.id}/lock",
            headers=admin_auth_headers,
            json={"reason": "Tự khóa"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Không thể tự khóa tài khoản của chính mình."

    def test_cannot_lock_already_locked_user(self, client, admin_auth_headers, locked_user):
        """Test khóa tài khoản đã bị khóa từ trước trả về 400."""
        response = client.post(
            f"/api/users/{locked_user.id}/lock",
            headers=admin_auth_headers,
            json={"reason": "Khóa lại"},
        )
        assert response.status_code == 400
        assert "đã bị khóa từ trước" in response.json()["detail"]

    def test_cannot_unlock_unlocked_user(self, client, admin_auth_headers, trainee_user):
        """Test mở khóa tài khoản đang không bị khóa trả về 400."""
        response = client.post(
            f"/api/users/{trainee_user.id}/unlock",
            headers=admin_auth_headers,
        )
        assert response.status_code == 400
        assert "không ở trạng thái bị khóa" in response.json()["detail"]

    def test_non_admin_cannot_lock_account(self, client, trainee_auth_headers, trainer_user):
        """Test người dùng không có quyền không được phép khóa tài khoản (403 Forbidden)."""
        response = client.post(
            f"/api/users/{trainer_user.id}/lock",
            headers=trainee_auth_headers,
            json={"reason": "Khóa trái phép"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Bạn không có quyền thực hiện hành động này."
