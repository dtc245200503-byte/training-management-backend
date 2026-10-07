import pytest


class TestRBACS1_05:
    def test_get_current_user_profile_rbac(self, client, admin_auth_headers, trainee_auth_headers, trainer_auth_headers):
        """Test endpoint /api/auth/me trả về đầy đủ vai trò và danh sách quyền hạn cho từng loại tài khoản."""
        # Admin profile
        resp_admin = client.get("/api/auth/me", headers=admin_auth_headers)
        assert resp_admin.status_code == 200
        data_admin = resp_admin.json()
        assert "ADMIN" in data_admin["roles"]
        assert "user:read" in data_admin["permissions"]
        assert "user:create" in data_admin["permissions"]
        assert "user:lock" in data_admin["permissions"]

        # Trainer profile
        resp_trainer = client.get("/api/auth/me", headers=trainer_auth_headers)
        assert resp_trainer.status_code == 200
        data_trainer = resp_trainer.json()
        assert "TRAINER" in data_trainer["roles"]
        assert "course:manage" in data_trainer["permissions"]
        assert "user:create" not in data_trainer["permissions"]

        # Trainee profile
        resp_trainee = client.get("/api/auth/me", headers=trainee_auth_headers)
        assert resp_trainee.status_code == 200
        data_trainee = resp_trainee.json()
        assert "TRAINEE" in data_trainee["roles"]
        assert "course:read" in data_trainee["permissions"]
        assert "course:manage" not in data_trainee["permissions"]
        assert "user:read" not in data_trainee["permissions"]

    def test_rbac_backend_api_enforcement(self, client, admin_auth_headers, trainee_auth_headers):
        """Test RBAC được kiểm tra nghiêm ngặt tại Backend API: Admin được truy cập, Trainee bị 403 Forbidden."""
        # Admin truy cập danh sách người dùng -> 200 OK
        resp_admin = client.get("/api/users", headers=admin_auth_headers)
        assert resp_admin.status_code == 200

        # Trainee truy cập danh sách người dùng -> 403 Forbidden
        resp_trainee = client.get("/api/users", headers=trainee_auth_headers)
        assert resp_trainee.status_code == 403
        assert resp_trainee.json()["detail"] == "Bạn không có quyền thực hiện hành động này."

    def test_list_roles_and_permissions(self, client, admin_auth_headers):
        """Test các endpoint lấy danh mục vai trò và quyền hạn."""
        # Danh mục vai trò
        resp_roles = client.get("/api/roles", headers=admin_auth_headers)
        assert resp_roles.status_code == 200
        roles_data = resp_roles.json()["items"]
        role_names = [r["name"] for r in roles_data]
        assert "ADMIN" in role_names
        assert "TRAINER" in role_names
        assert "TRAINEE" in role_names

        # Danh mục quyền hạn
        resp_perms = client.get("/api/permissions", headers=admin_auth_headers)
        assert resp_perms.status_code == 200
        perms_data = resp_perms.json()
        perm_codes = [p["code"] for p in perms_data]
        assert "user:read" in perm_codes
        assert "user:create" in perm_codes
        assert "role:assign" in perm_codes
        assert "user:lock" in perm_codes
