import pytest
from fastapi import status
from app.models.consultation_lead import ConsultationLead


class TestAssignLeadS2_10:
    def test_assign_lead_unauthenticated(self, client):
        response = client.post("/api/leads/1/assign", json={"user_id": 1})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_assign_lead_forbidden_trainee(self, client, trainee_auth_headers):
        response = client.post("/api/leads/1/assign", json={"user_id": 1}, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_assign_lead_success_auto_updates_status(self, client, admin_auth_headers, trainer_user, db_session):
        lead = ConsultationLead(
            full_name="Nguyễn Văn Cần Tư Vấn",
            email="can_tu_van@example.com",
            phone="0919191919",
            status="NEW",
        )
        db_session.add(lead)
        db_session.commit()

        payload = {"user_id": trainer_user.id}
        res = client.post(f"/api/leads/{lead.id}/assign", json=payload, headers=admin_auth_headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["assigned_to_id"] == trainer_user.id
        assert data["assigned_to_name"] == trainer_user.full_name
        assert data["assigned_at"] is not None
        # Tự động chuyển từ NEW sang CONTACTED
        assert data["status"] == "CONTACTED"

    def test_assign_lead_to_nonexistent_user(self, client, admin_auth_headers, db_session):
        lead = ConsultationLead(
            full_name="Lead Test",
            email="lead@example.com",
            phone="0911000000",
            status="NEW",
        )
        db_session.add(lead)
        db_session.commit()

        payload = {"user_id": 99999}
        res = client.post(f"/api/leads/{lead.id}/assign", json=payload, headers=admin_auth_headers)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "không tồn tại" in res.json()["detail"].lower() or "hóa" in res.json()["detail"].lower()

    def test_assign_lead_to_locked_user(self, client, admin_auth_headers, locked_user, db_session):
        lead = ConsultationLead(
            full_name="Lead Locked Assign",
            email="lead_locked@example.com",
            phone="0911000001",
            status="NEW",
        )
        db_session.add(lead)
        db_session.commit()

        payload = {"user_id": locked_user.id}
        res = client.post(f"/api/leads/{lead.id}/assign", json=payload, headers=admin_auth_headers)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "khóa" in res.json()["detail"].lower()
