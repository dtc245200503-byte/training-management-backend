import pytest
from fastapi import status
from app.models.consultation_lead import ConsultationLead


class TestLeadManagementS2_09:
    def test_list_leads_unauthenticated(self, client):
        response = client.get("/api/leads")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_leads_forbidden_trainee(self, client, trainee_auth_headers):
        response = client.get("/api/leads", headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_lead_detail_and_not_found(self, client, admin_auth_headers, db_session):
        lead = ConsultationLead(
            full_name="Hoàng Thị Thảo",
            email="thao@example.com",
            phone="0911223344",
            status="NEW",
        )
        db_session.add(lead)
        db_session.commit()

        res = client.get(f"/api/leads/{lead.id}", headers=admin_auth_headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["id"] == lead.id
        assert data["full_name"] == "Hoàng Thị Thảo"
        assert data["status"] == "NEW"

        not_found = client.get("/api/leads/99999", headers=admin_auth_headers)
        assert not_found.status_code == status.HTTP_404_NOT_FOUND

    def test_update_lead_status_and_notes(self, client, admin_auth_headers, db_session):
        lead = ConsultationLead(
            full_name="Ngô Bá Khá",
            email="nbk@example.com",
            phone="0988776655",
            status="NEW",
        )
        db_session.add(lead)
        db_session.commit()

        # Cập nhật hợp lệ
        update_payload = {
            "status": "CONSULTING",
            "admin_notes": "Đã gọi điện tư vấn lần 1, khách hẹn cuối tuần",
        }
        res = client.put(f"/api/leads/{lead.id}", json=update_payload, headers=admin_auth_headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["status"] == "CONSULTING"
        assert data["admin_notes"] == "Đã gọi điện tư vấn lần 1, khách hẹn cuối tuần"

    def test_update_lead_invalid_status(self, client, admin_auth_headers, db_session):
        lead = ConsultationLead(
            full_name="Test Bad Status",
            email="badstatus@example.com",
            phone="0901010101",
            status="NEW",
        )
        db_session.add(lead)
        db_session.commit()

        bad_payload = {"status": "INVALID_STATUS_NAME"}
        res = client.put(f"/api/leads/{lead.id}", json=bad_payload, headers=admin_auth_headers)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "không hợp lệ" in res.json()["detail"].lower()

    def test_delete_lead_success(self, client, admin_auth_headers, db_session):
        lead = ConsultationLead(
            full_name="Delete Me",
            email="deleteme@example.com",
            phone="0902020202",
            status="NEW",
        )
        db_session.add(lead)
        db_session.commit()

        del_res = client.delete(f"/api/leads/{lead.id}", headers=admin_auth_headers)
        assert del_res.status_code == status.HTTP_200_OK

        get_res = client.get(f"/api/leads/{lead.id}", headers=admin_auth_headers)
        assert get_res.status_code == status.HTTP_404_NOT_FOUND
