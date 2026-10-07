import pytest


class TestUserManagementS1_08:
    def test_list_users_with_pagination_and_search(self, client, admin_auth_headers, trainee_user, trainer_user):
        """Test Admin xem danh sách người dùng có phân trang và tìm kiếm."""
        response = client.get("/api/users?skip=0&limit=10", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) <= 10

        # Không bao giờ để lộ mật khẩu trong danh sách
        for item in data["items"]:
            assert "password" not in item
            assert "password_hash" not in item

        # Tìm kiếm theo email
        search_resp = client.get(f"/api/users?search={trainee_user.email}", headers=admin_auth_headers)
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert search_data["total"] >= 1
        assert any(u["email"] == trainee_user.email for u in search_data["items"])

        # Lọc theo vai trò
        filter_resp = client.get("/api/users?role=TRAINER", headers=admin_auth_headers)
        assert filter_resp.status_code == 200
        filter_data = filter_resp.json()
        for u in filter_data["items"]:
            assert "TRAINER" in u["roles"]

    def test_get_user_detail(self, client, admin_auth_headers, trainee_user):
        """Test xem thông tin chi tiết một người dùng."""
        response = client.get(f"/api/users/{trainee_user.id}", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == trainee_user.id
        assert data["email"] == trainee_user.email
        assert "password" not in data
        assert "password_hash" not in data
        assert "TRAINEE" in data["roles"]

    def test_get_nonexistent_user_detail(self, client, admin_auth_headers):
        """Test xem người dùng không tồn tại trả về 404."""
        response = client.get("/api/users/999999", headers=admin_auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Không tìm thấy người dùng."

    def test_create_user_success_and_login(self, client, admin_auth_headers):
        """Test tạo người dùng mới thành công và người dùng mới có thể đăng nhập ngay lập tức."""
        response = client.post(
            "/api/users",
            headers=admin_auth_headers,
            json={
                "email": "new.member@example.com",
                "password": "InitialPassword123",
                "full_name": "Thành viên mới",
                "roles": ["TRAINEE"],
                "is_active": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new.member@example.com"
        assert data["full_name"] == "Thành viên mới"
        assert "password" not in data
        assert "password_hash" not in data
        assert "TRAINEE" in data["roles"]

        # Người dùng mới đăng nhập thành công
        login_resp = client.post(
            "/api/auth/login",
            json={
                "email": "new.member@example.com",
                "password": "InitialPassword123",
            },
        )
        assert login_resp.status_code == 200

    def test_create_user_duplicate_email_rejected(self, client, admin_auth_headers, trainee_user):
        """Test từ chối tạo người dùng với email đã tồn tại trong hệ thống (400)."""
        response = client.post(
            "/api/users",
            headers=admin_auth_headers,
            json={
                "email": trainee_user.email,
                "password": "AnotherPassword123",
                "full_name": "Trùng email",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Email đã tồn tại trong hệ thống."

    def test_update_user_info(self, client, admin_auth_headers, trainee_user):
        """Test cập nhật họ tên và email của người dùng."""
        response = client.put(
            f"/api/users/{trainee_user.id}",
            headers=admin_auth_headers,
            json={
                "full_name": "Tên Đã Cập Nhật",
                "email": "updated.trainee@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Tên Đã Cập Nhật"
        assert data["email"] == "updated.trainee@example.com"

    def test_delete_user_success(self, client, admin_auth_headers):
        """Test xóa người dùng thành công."""
        # Tạo người dùng để xóa
        create_resp = client.post(
            "/api/users",
            headers=admin_auth_headers,
            json={
                "email": "to_be_deleted@example.com",
                "password": "password123",
                "full_name": "User To Delete",
            },
        )
        user_id = create_resp.json()["id"]

        # Xóa
        del_resp = client.delete(f"/api/users/{user_id}", headers=admin_auth_headers)
        assert del_resp.status_code == 200

        # Kiểm tra không còn tồn tại
        get_resp = client.get(f"/api/users/{user_id}", headers=admin_auth_headers)
        assert get_resp.status_code == 404

    def test_admin_cannot_delete_self(self, client, admin_user, admin_auth_headers):
        """Test Admin không được phép tự xóa tài khoản của chính mình (400)."""
        response = client.delete(f"/api/users/{admin_user.id}", headers=admin_auth_headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Không thể tự xóa tài khoản của chính mình."
