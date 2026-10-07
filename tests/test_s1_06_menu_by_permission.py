import pytest


class TestMenuByPermissionS1_06:
    def test_admin_gets_full_menu(self, client, admin_auth_headers):
        """Test Admin nhận được menu đầy đủ gồm quản lý người dùng, khóa học, báo cáo và cài đặt."""
        response = client.get("/api/menu", headers=admin_auth_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        menu_keys = [item["key"] for item in items]

        assert "dashboard" in menu_keys
        assert "users" in menu_keys
        assert "courses" in menu_keys
        assert "reports" in menu_keys
        assert "settings" in menu_keys

        # Kiểm tra sub-menu của Quản lý người dùng
        user_menu = next(i for i in items if i["key"] == "users")
        sub_keys = [c["key"] for c in user_menu["children"]]
        assert "users-list" in sub_keys
        assert "roles-manage" in sub_keys

    def test_trainer_gets_trainer_menu(self, client, trainer_auth_headers):
        """Test Trainer nhận được menu đào tạo, khóa học và báo cáo, không có quản trị người dùng hay cài đặt."""
        response = client.get("/api/menu", headers=trainer_auth_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        menu_keys = [item["key"] for item in items]

        assert "dashboard" in menu_keys
        assert "courses" in menu_keys
        assert "my-courses" in menu_keys
        assert "reports" in menu_keys

        # Tuyệt đối không có menu quản trị nhạy cảm
        assert "users" not in menu_keys
        assert "settings" not in menu_keys

    def test_trainee_gets_trainee_menu(self, client, trainee_auth_headers):
        """Test Trainee chỉ nhận được Dashboard và Khóa học của tôi."""
        response = client.get("/api/menu", headers=trainee_auth_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        menu_keys = [item["key"] for item in items]

        assert "dashboard" in menu_keys
        assert "my-courses" in menu_keys

        # Không thấy các menu quản lý đào tạo hay hệ thống
        assert "users" not in menu_keys
        assert "courses" not in menu_keys
        assert "reports" not in menu_keys
        assert "settings" not in menu_keys

    def test_auth_menu_alias_endpoint(self, client, trainee_auth_headers):
        """Test endpoint alias /api/auth/menu hoạt động tương đương."""
        response = client.get("/api/auth/menu", headers=trainee_auth_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        menu_keys = [item["key"] for item in items]
        assert "dashboard" in menu_keys

    def test_unauthenticated_menu_access_rejected(self, client):
        """Test truy cập menu khi chưa đăng nhập trả về 401."""
        response = client.get("/api/menu")
        assert response.status_code == 401
