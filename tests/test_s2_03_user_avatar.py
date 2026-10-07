import io
import pytest
from fastapi import status


class TestUserAvatarS2_03:
    def test_upload_avatar_unauthenticated(self, client):
        file_content = b"\x89PNG\r\n\x1a\nfake_png_binary_data"
        files = {"file": ("avatar.png", io.BytesIO(file_content), "image/png")}
        response = client.post("/api/profile/avatar", files=files)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_avatar_png_success(self, client, trainee_auth_headers):
        file_content = b"\x89PNG\r\n\x1a\nfake_png_binary_data"
        files = {"file": ("my_avatar.png", io.BytesIO(file_content), "image/png")}
        response = client.post("/api/profile/avatar", files=files, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "avatar_url" in data
        assert data["avatar_url"].startswith("/uploads/avatars/")
        assert data["avatar_url"].endswith(".png")

        # Kiểm tra qua GET /api/profile
        profile_res = client.get("/api/profile", headers=trainee_auth_headers)
        assert profile_res.status_code == status.HTTP_200_OK
        assert profile_res.json()["avatar_url"] == data["avatar_url"]

        # Kiểm tra file tĩnh có truy cập được qua GET /uploads/...
        static_res = client.get(data["avatar_url"])
        assert static_res.status_code == status.HTTP_200_OK
        assert static_res.content == file_content

    def test_upload_avatar_jpeg_success(self, client, trainee_auth_headers):
        file_content = b"\xff\xd8\xff\xe0fake_jpeg_binary"
        files = {"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")}
        response = client.post("/api/profile/avatar", files=files, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["avatar_url"].endswith(".jpg")

    def test_upload_avatar_invalid_file_type(self, client, trainee_auth_headers):
        file_content = b"console.log('malicious');"
        files = {"file": ("script.js", io.BytesIO(file_content), "text/javascript")}
        response = client.post("/api/profile/avatar", files=files, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "định dạng" in response.json()["detail"].lower() or "hợp lệ" in response.json()["detail"].lower()

    def test_upload_avatar_file_too_large(self, client, trainee_auth_headers):
        # 6MB (vượt quá 5MB)
        large_content = b"0" * (6 * 1024 * 1024)
        files = {"file": ("large.png", io.BytesIO(large_content), "image/png")}
        response = client.post("/api/profile/avatar", files=files, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "5mb" in response.json()["detail"].lower() or "kích thước" in response.json()["detail"].lower()
