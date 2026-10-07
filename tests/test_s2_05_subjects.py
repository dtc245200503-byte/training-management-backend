import pytest
from fastapi import status


class TestSubjectsS2_05:
    def test_list_subjects_unauthenticated(self, client):
        response = client.get("/api/subjects")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_subject_forbidden_trainee(self, client, trainee_auth_headers):
        payload = {
            "code": "SUB-REACT",
            "name": "ReactJS Cơ bản",
        }
        response = client.post("/api/subjects", json=payload, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_subject_success_admin(self, client, admin_auth_headers):
        payload = {
            "code": "SUB-PYTHON",
            "name": "Python Backend Development",
            "description": "Lập trình backend với FastAPI",
            "hours": 45,
        }
        response = client.post("/api/subjects", json=payload, headers=admin_auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["code"] == "SUB-PYTHON"
        assert data["name"] == "Python Backend Development"
        assert data["hours"] == 45
        assert data["status"] == "ACTIVE"
        assert "id" in data

    def test_create_subject_duplicate_code(self, client, admin_auth_headers):
        payload = {
            "code": "SUB-DUP",
            "name": "Môn học 1",
        }
        res1 = client.post("/api/subjects", json=payload, headers=admin_auth_headers)
        assert res1.status_code == status.HTTP_201_CREATED

        res2 = client.post("/api/subjects", json=payload, headers=admin_auth_headers)
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert "tồn tại" in res2.json()["detail"].lower() or "mã" in res2.json()["detail"].lower()

    def test_get_subject_by_id_and_not_found(self, client, admin_auth_headers):
        payload = {"code": "SUB-DETAIL", "name": "Detail Test"}
        res = client.post("/api/subjects", json=payload, headers=admin_auth_headers)
        sub_id = res.json()["id"]

        get_res = client.get(f"/api/subjects/{sub_id}", headers=admin_auth_headers)
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.json()["code"] == "SUB-DETAIL"

        not_found = client.get("/api/subjects/88888", headers=admin_auth_headers)
        assert not_found.status_code == status.HTTP_404_NOT_FOUND

    def test_update_subject_success(self, client, admin_auth_headers):
        payload = {"code": "SUB-UPDATE", "name": "Original Name"}
        res = client.post("/api/subjects", json=payload, headers=admin_auth_headers)
        sub_id = res.json()["id"]

        update_payload = {"name": "Updated Subject Name", "hours": 60}
        put_res = client.put(f"/api/subjects/{sub_id}", json=update_payload, headers=admin_auth_headers)
        assert put_res.status_code == status.HTTP_200_OK
        assert put_res.json()["name"] == "Updated Subject Name"
        assert put_res.json()["hours"] == 60

    def test_delete_subject_success(self, client, admin_auth_headers):
        payload = {"code": "SUB-DELETE", "name": "To Delete"}
        res = client.post("/api/subjects", json=payload, headers=admin_auth_headers)
        sub_id = res.json()["id"]

        del_res = client.delete(f"/api/subjects/{sub_id}", headers=admin_auth_headers)
        assert del_res.status_code == status.HTTP_200_OK

        get_res = client.get(f"/api/subjects/{sub_id}", headers=admin_auth_headers)
        assert get_res.status_code == status.HTTP_404_NOT_FOUND
