import pytest
from fastapi import status


class TestUserProfileS2_02:
    def test_get_profile_unauthenticated(self, client):
        response = client.get("/api/profile")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_profile_success(self, client, trainee_auth_headers, trainee_user):
        response = client.get("/api/profile", headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == trainee_user.id
        assert data["email"] == trainee_user.email
        assert data["full_name"] == trainee_user.full_name
        assert "roles" in data
        assert "permissions" in data

    def test_update_profile_success(self, client, trainee_auth_headers, trainee_user):
        payload = {
            "full_name": "Trainee Updated Name",
            "phone_number": "0987654321",
            "bio": "Học viên năng động",
            "address": "123 Đường ABC, Hà Nội",
            "date_of_birth": "2000-01-15",
            "gender": "male",
        }
        response = client.put("/api/profile", json=payload, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Trainee Updated Name"
        assert data["phone_number"] == "0987654321"
        assert data["bio"] == "Học viên năng động"
        assert data["address"] == "123 Đường ABC, Hà Nội"
        assert data["date_of_birth"] == "2000-01-15"
        assert data["gender"] == "male"

        # Kiểm tra lại bằng GET
        get_res = client.get("/api/profile", headers=trainee_auth_headers)
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.json()["phone_number"] == "0987654321"

    def test_update_profile_partial(self, client, trainee_auth_headers):
        payload = {
            "bio": "Chỉ cập nhật bio",
        }
        response = client.put("/api/profile", json=payload, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["bio"] == "Chỉ cập nhật bio"
        assert data["full_name"] == "Trainee Test"

    def test_update_profile_empty_full_name_validation(self, client, trainee_auth_headers):
        payload = {
            "full_name": "   ",
        }
        response = client.put("/api/profile", json=payload, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
