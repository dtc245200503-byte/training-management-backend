import pytest
from fastapi import status
from app.models.consultation_lead import ConsultationLead
from app.models.training_program import TrainingProgram


class TestPublicConsultationS2_08:
    def test_submit_public_consultation_success(self, client, db_session):
        payload = {
            "full_name": "Nguyễn Thị Mai",
            "email": "nguyenmai@example.com",
            "phone": "0912345678",
            "notes": "Muốn tư vấn khóa học lập trình Python",
        }
        response = client.post("/api/public/consultations", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] > 0
        assert "thành công" in data["message"].lower()

        # Kiểm tra bản ghi trong CSDL
        lead = db_session.query(ConsultationLead).filter(ConsultationLead.id == data["id"]).first()
        assert lead is not None
        assert lead.full_name == "Nguyễn Thị Mai"
        assert lead.email == "nguyenmai@example.com"
        assert lead.phone == "0912345678"
        assert lead.status == "NEW"

    def test_submit_consultation_alias_endpoint(self, client):
        payload = {
            "full_name": "Trần Văn Bình",
            "email": "tranbinh@example.com",
            "phone": "0988776655",
        }
        response = client.post("/api/consultations", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["id"] > 0

    def test_submit_public_consultation_honeypot_trap(self, client, db_session):
        # Bot điền vào trường honeypot
        payload = {
            "full_name": "Spam Bot",
            "email": "spambot@example.com",
            "phone": "0900000000",
            "honeypot": "I am a hidden bot value",
        }
        initial_count = db_session.query(ConsultationLead).count()

        response = client.post("/api/public/consultations", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == 0

        # Xác nhận không có bản ghi nào bị ghi vào DB
        new_count = db_session.query(ConsultationLead).count()
        assert new_count == initial_count

    def test_submit_invalid_phone(self, client):
        payload = {
            "full_name": "Lê Lỗi Số",
            "email": "leloi@example.com",
            "phone": "abc-invalid-phone",
        }
        response = client.post("/api/public/consultations", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "điện thoại" in response.json()["detail"].lower()

    def test_submit_with_program_id(self, client, db_session):
        prog = TrainingProgram(code="PROG-WEB", name="Web Dev", status="ACTIVE")
        db_session.add(prog)
        db_session.commit()

        payload = {
            "full_name": "Phạm Văn Cường",
            "email": "phamcuong@example.com",
            "phone": "0934567890",
            "program_id": prog.id,
        }
        response = client.post("/api/public/consultations", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        lead = db_session.query(ConsultationLead).filter(ConsultationLead.id == response.json()["id"]).first()
        assert lead.program_id == prog.id

    def test_submit_with_nonexistent_program_id(self, client):
        payload = {
            "full_name": "Phạm Văn Lỗi",
            "email": "phamloi@example.com",
            "phone": "0934567890",
            "program_id": 99999,
        }
        response = client.post("/api/public/consultations", json=payload)
        assert response.status_code == status.HTTP_404_NOT_FOUND
