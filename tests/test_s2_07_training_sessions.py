from datetime import datetime, timezone, timedelta
import pytest
from fastapi import status


class TestTrainingSessionsS2_07:
    def test_list_sessions_unauthenticated(self, client):
        response = client.get("/api/training-sessions")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_session_forbidden_trainee(self, client, trainee_auth_headers):
        now = datetime.now(timezone.utc)
        payload = {
            "code": "SESS-FORBIDDEN",
            "name": "Lớp ReactJS K15",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=30)).isoformat(),
        }
        response = client.post("/api/training-sessions", json=payload, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_session_invalid_dates(self, client, admin_auth_headers):
        now = datetime.now(timezone.utc)
        payload = {
            "code": "SESS-BAD-DATE",
            "name": "Lớp Lỗi Ngày",
            "start_date": (now + timedelta(days=10)).isoformat(),
            "end_date": now.isoformat(),
        }
        response = client.post("/api/training-sessions", json=payload, headers=admin_auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ngày" in response.json()["detail"].lower() or "thời gian" in response.json()["detail"].lower()

    def test_create_session_success(self, client, admin_auth_headers, trainer_user):
        now = datetime.now(timezone.utc)
        payload = {
            "code": "SESS-PY01",
            "name": "Lớp Python Backend K01",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=60)).isoformat(),
            "location": "Phòng Lab 302",
            "max_trainees": 25,
            "trainer_id": trainer_user.id,
        }
        response = client.post("/api/training-sessions", json=payload, headers=admin_auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["code"] == "SESS-PY01"
        assert data["name"] == "Lớp Python Backend K01"
        assert data["location"] == "Phòng Lab 302"
        assert data["max_trainees"] == 25
        assert data["trainer_id"] == trainer_user.id
        assert data["trainer_name"] == trainer_user.full_name
        assert "id" in data

    def test_update_session_success_and_invalid_date(self, client, admin_auth_headers):
        payload = {
            "code": "SESS-UPDATE",
            "name": "Lớp Thử Nghiệm",
            "start_date": "2026-05-01T08:00:00Z",
            "end_date": "2026-06-01T17:00:00Z",
        }
        res = client.post("/api/training-sessions", json=payload, headers=admin_auth_headers)
        assert res.status_code == status.HTTP_201_CREATED
        session_id = res.json()["id"]

        # Cập nhật hợp lệ
        update_payload = {"name": "Lớp Thử Nghiệm Cập Nhật", "location": "Zoom Online"}
        put_res = client.put(f"/api/training-sessions/{session_id}", json=update_payload, headers=admin_auth_headers)
        assert put_res.status_code == status.HTTP_200_OK
        assert put_res.json()["name"] == "Lớp Thử Nghiệm Cập Nhật"
        assert put_res.json()["location"] == "Zoom Online"

        # Cập nhật ngày kết thúc trước ngày bắt đầu -> 400
        bad_date_payload = {"end_date": "2026-04-01T00:00:00Z"}
        bad_put = client.put(f"/api/training-sessions/{session_id}", json=bad_date_payload, headers=admin_auth_headers)
        assert bad_put.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_session_success(self, client, admin_auth_headers):
        payload = {
            "code": "SESS-DEL",
            "name": "Lớp Sắp Bị Xóa",
            "start_date": "2026-07-01T08:00:00Z",
            "end_date": "2026-08-01T17:00:00Z",
        }
        res = client.post("/api/training-sessions", json=payload, headers=admin_auth_headers)
        assert res.status_code == status.HTTP_201_CREATED
        session_id = res.json()["id"]

        del_res = client.delete(f"/api/training-sessions/{session_id}", headers=admin_auth_headers)
        assert del_res.status_code == status.HTTP_200_OK

        get_res = client.get(f"/api/training-sessions/{session_id}", headers=admin_auth_headers)
        assert get_res.status_code == status.HTTP_404_NOT_FOUND
