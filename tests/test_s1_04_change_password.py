import pytest


class TestChangePasswordS1_04:
    def test_change_password_success(self, client, test_user):
        """Test đổi mật khẩu thành công khi nhập đúng mật khẩu hiện tại."""
        # Đăng nhập lấy access token
        login_resp = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        access_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        new_password = "BrandNewPassword123"
        response = client.post(
            "/api/auth/change-password",
            headers=headers,
            json={
                "old_password": "password123",
                "new_password": new_password,
                "confirm_password": new_password,
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Đổi mật khẩu thành công."

        # Mật khẩu cũ không còn đăng nhập được
        old_login = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        assert old_login.status_code == 401

        # Mật khẩu mới đăng nhập thành công
        new_login = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": new_password},
        )
        assert new_login.status_code == 200

    def test_change_password_wrong_old_password(self, client, test_user):
        """Test đổi mật khẩu với mật khẩu cũ sai trả về 400."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        access_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.post(
            "/api/auth/change-password",
            headers=headers,
            json={
                "old_password": "wrong_old_password",
                "new_password": "NewValidPassword123",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Mật khẩu hiện tại không chính xác."

    def test_change_password_same_new_password_rejected(self, client, test_user):
        """Test mật khẩu mới trùng với mật khẩu cũ bị từ chối với 400."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        access_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.post(
            "/api/auth/change-password",
            headers=headers,
            json={
                "old_password": "password123",
                "new_password": "password123",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Mật khẩu mới không được trùng với mật khẩu cũ."

    def test_change_password_mismatched_confirm_password(self, client, test_user):
        """Test mật khẩu xác nhận không khớp trả về 400."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        access_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.post(
            "/api/auth/change-password",
            headers=headers,
            json={
                "old_password": "password123",
                "new_password": "NewPassword123",
                "confirm_password": "DifferentPassword123",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Mật khẩu xác nhận không khớp."

    def test_change_password_unauthenticated_rejected(self, client):
        """Test đổi mật khẩu khi chưa xác thực trả về 401 Unauthorized."""
        response = client.post(
            "/api/auth/change-password",
            json={
                "old_password": "password123",
                "new_password": "NewPassword123",
            },
        )
        assert response.status_code == 401

    def test_change_password_revokes_previous_refresh_tokens(self, client, test_user):
        """Test đổi mật khẩu thu hồi mọi refresh token hiện tại để bảo đảm an toàn."""
        login_resp = client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        access_token = login_resp.json()["access_token"]
        refresh_token = login_resp.json()["refresh_token"]

        # Đổi mật khẩu
        client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": "password123",
                "new_password": "BrandNewPassword123",
            },
        )

        # Refresh token trước đó bị vô hiệu hóa
        refresh_resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401
        assert refresh_resp.json()["detail"] == "Refresh token đã bị thu hồi."
