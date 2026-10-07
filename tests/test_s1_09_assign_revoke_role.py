import pytest


class TestAssignRevokeRoleS1_09:
    def test_assign_role_success(self, client, admin_auth_headers, trainee_user):
        """Test Admin gán vai trò mới cho người dùng (ví dụ thăng hạng lên TRAINER)."""
        response = client.post(
            f"/api/users/{trainee_user.id}/roles",
            headers=admin_auth_headers,
            json={"roles": ["TRAINER"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Gán vai trò thành công."
        assert "TRAINER" in data["roles"]
        assert "TRAINEE" not in data["roles"]

        # Kiểm tra chi tiết user phản ánh vai trò mới
        user_detail = client.get(f"/api/users/{trainee_user.id}", headers=admin_auth_headers).json()
        assert "TRAINER" in user_detail["roles"]
        assert "course:manage" in user_detail["permissions"]

    def test_revoke_role_success(self, client, admin_auth_headers, trainee_user):
        """Test Admin thu hồi một vai trò của người dùng."""
        # Đầu tiên cấp cả 2 vai trò TRAINEE và TRAINER
        client.post(
            f"/api/users/{trainee_user.id}/roles",
            headers=admin_auth_headers,
            json={"roles": ["TRAINEE", "TRAINER"]},
        )

        # Thu hồi vai trò TRAINER
        response = client.delete(
            f"/api/users/{trainee_user.id}/roles/TRAINER",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "TRAINER" not in data["roles"]
        assert "TRAINEE" in data["roles"]

    def test_assign_invalid_role_rejected(self, client, admin_auth_headers, trainee_user):
        """Test gán vai trò không tồn tại trong hệ thống trả về 400."""
        response = client.post(
            f"/api/users/{trainee_user.id}/roles",
            headers=admin_auth_headers,
            json={"roles": ["SUPER_HERO"]},
        )
        assert response.status_code == 400
        assert "không tồn tại" in response.json()["detail"]

    def test_revoke_unassigned_role_rejected(self, client, admin_auth_headers, trainee_user):
        """Test thu hồi vai trò mà người dùng không sở hữu trả về 400."""
        response = client.delete(
            f"/api/users/{trainee_user.id}/roles/ADMIN",
            headers=admin_auth_headers,
        )
        assert response.status_code == 400
        assert "không có vai trò" in response.json()["detail"]

    def test_cannot_revoke_last_admin(self, client, admin_user, admin_auth_headers):
        """Test hệ thống ngăn chặn việc thu hồi vai trò ADMIN của quản trị viên duy nhất (400)."""
        response = client.delete(
            f"/api/users/{admin_user.id}/roles/ADMIN",
            headers=admin_auth_headers,
        )
        assert response.status_code == 400
        assert "quản trị viên duy nhất" in response.json()["detail"]

    def test_non_admin_cannot_assign_roles(self, client, trainee_auth_headers, trainee_user):
        """Test tài khoản không có quyền không thể gán vai trò (403 Forbidden)."""
        response = client.post(
            f"/api/users/{trainee_user.id}/roles",
            headers=trainee_auth_headers,
            json={"roles": ["ADMIN"]},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Bạn không có quyền thực hiện hành động này."
