import pytest
from fastapi import status


class TestTrainingProgramsS2_04:
    def test_list_programs_unauthenticated(self, client):
        response = client.get("/api/training-programs")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_program_forbidden_trainee(self, client, trainee_auth_headers):
        payload = {
            "code": "PROG-01",
            "name": "Chương trình Fullstack Developer",
            "description": "Đào tạo lập trình viên fullstack từ cơ bản đến nâng cao",
        }
        response = client.post("/api/training-programs", json=payload, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_program_success_admin(self, client, admin_auth_headers):
        payload = {
            "code": "PROG-FULLSTACK",
            "name": "Fullstack Web Development",
            "description": "Khóa học Fullstack",
            "duration_hours": 120,
        }
        response = client.post("/api/training-programs", json=payload, headers=admin_auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["code"] == "PROG-FULLSTACK"
        assert data["name"] == "Fullstack Web Development"
        assert data["duration_hours"] == 120
        assert data["status"] == "ACTIVE"
        assert "id" in data

    def test_create_program_duplicate_code(self, client, admin_auth_headers):
        payload = {
            "code": "PROG-DUP",
            "name": "Chương trình 1",
        }
        res1 = client.post("/api/training-programs", json=payload, headers=admin_auth_headers)
        assert res1.status_code == status.HTTP_201_CREATED

        res2 = client.post("/api/training-programs", json=payload, headers=admin_auth_headers)
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert "tồn tại" in res2.json()["detail"].lower() or "mã" in res2.json()["detail"].lower()

    def test_get_program_by_id_and_not_found(self, client, admin_auth_headers):
        payload = {"code": "PROG-DETAIL", "name": "Detail Test"}
        res = client.post("/api/training-programs", json=payload, headers=admin_auth_headers)
        prog_id = res.json()["id"]

        get_res = client.get(f"/api/training-programs/{prog_id}", headers=admin_auth_headers)
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.json()["code"] == "PROG-DETAIL"

        not_found_res = client.get("/api/training-programs/99999", headers=admin_auth_headers)
        assert not_found_res.status_code == status.HTTP_404_NOT_FOUND

    def test_update_program_success(self, client, admin_auth_headers):
        payload = {"code": "PROG-UPDATE", "name": "Before Update"}
        res = client.post("/api/training-programs", json=payload, headers=admin_auth_headers)
        prog_id = res.json()["id"]

        update_payload = {"name": "After Update", "duration_hours": 90}
        put_res = client.put(f"/api/training-programs/{prog_id}", json=update_payload, headers=admin_auth_headers)
        assert put_res.status_code == status.HTTP_200_OK
        assert put_res.json()["name"] == "After Update"
        assert put_res.json()["duration_hours"] == 90

    def test_delete_program_success(self, client, admin_auth_headers):
        payload = {"code": "PROG-DELETE", "name": "To Delete"}
        res = client.post("/api/training-programs", json=payload, headers=admin_auth_headers)
        prog_id = res.json()["id"]

        del_res = client.delete(f"/api/training-programs/{prog_id}", headers=admin_auth_headers)
        assert del_res.status_code == status.HTTP_200_OK

        # Sau khi xóa thì get lại trả về 404
        get_res = client.get(f"/api/training-programs/{prog_id}", headers=admin_auth_headers)
        assert get_res.status_code == status.HTTP_404_NOT_FOUND
