import pytest
from fastapi import status
from app.models.consultation_lead import ConsultationLead
from app.models.training_program import TrainingProgram


class TestSearchFilterLeadsS2_11:
    @pytest.fixture(autouse=True)
    def setup_leads(self, db_session, trainer_user):
        prog_a = TrainingProgram(code="PROG-A", name="Chương trình A", status="ACTIVE")
        prog_b = TrainingProgram(code="PROG-B", name="Chương trình B", status="ACTIVE")
        db_session.add_all([prog_a, prog_b])
        db_session.commit()

        lead1 = ConsultationLead(
            full_name="Đặng Văn Lâm",
            email="vanlam@example.com",
            phone="0901111111",
            status="NEW",
            program_id=prog_a.id,
        )
        lead2 = ConsultationLead(
            full_name="Quế Ngọc Hải",
            email="ngochai@example.com",
            phone="0902222222",
            status="CONTACTED",
            program_id=prog_b.id,
            assigned_to_id=trainer_user.id,
        )
        lead3 = ConsultationLead(
            full_name="Nguyễn Quang Hải",
            email="quanghai@example.com",
            phone="0903333333",
            status="NEW",
            program_id=prog_a.id,
        )
        db_session.add_all([lead1, lead2, lead3])
        db_session.commit()

        self.prog_a = prog_a
        self.prog_b = prog_b
        self.trainer = trainer_user

    def test_search_by_keyword(self, client, admin_auth_headers):
        # Tìm kiếm theo tên "Hải" -> 2 kết quả (Quế Ngọc Hải, Nguyễn Quang Hải)
        res = client.get("/api/leads?search=Hải", headers=admin_auth_headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total"] == 2
        names = [item["full_name"] for item in data["items"]]
        assert "Quế Ngọc Hải" in names
        assert "Nguyễn Quang Hải" in names

    def test_filter_by_status(self, client, admin_auth_headers):
        # Lọc theo status="CONTACTED" -> 1 kết quả
        res = client.get("/api/leads?status=CONTACTED", headers=admin_auth_headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["full_name"] == "Quế Ngọc Hải"

    def test_filter_by_program_id(self, client, admin_auth_headers):
        # Lọc theo program A -> 2 kết quả
        res = client.get(f"/api/leads?program_id={self.prog_a.id}", headers=admin_auth_headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total"] == 2

    def test_filter_by_assigned_to_id(self, client, admin_auth_headers):
        # Lọc theo trainer phụ trách -> 1 kết quả
        res = client.get(f"/api/leads?assigned_to_id={self.trainer.id}", headers=admin_auth_headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["assigned_to_id"] == self.trainer.id

    def test_pagination(self, client, admin_auth_headers):
        # Phân trang: limit=2, skip=0
        page1 = client.get("/api/leads?limit=2&skip=0", headers=admin_auth_headers)
        assert page1.status_code == status.HTTP_200_OK
        data1 = page1.json()
        assert data1["total"] == 3
        assert len(data1["items"]) == 2

        # Phân trang: limit=2, skip=2
        page2 = client.get("/api/leads?limit=2&skip=2", headers=admin_auth_headers)
        assert page2.status_code == status.HTTP_200_OK
        data2 = page2.json()
        assert data2["total"] == 3
        assert len(data2["items"]) == 1
