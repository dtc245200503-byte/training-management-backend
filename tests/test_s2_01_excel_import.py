from io import BytesIO
import openpyxl
import pytest
from fastapi import status
from app.models.user import User


def create_excel_file(headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


class TestExcelImportS2_01:
    def test_import_unauthenticated(self, client):
        excel_data = create_excel_file(["email", "full_name"], [["test@example.com", "Test"]])
        files = {"file": ("users.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/api/users/import-excel", files=files)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_import_forbidden_trainee(self, client, trainee_auth_headers):
        excel_data = create_excel_file(["email", "full_name"], [["test@example.com", "Test"]])
        files = {"file": ("users.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/api/users/import-excel", files=files, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_import_invalid_extension(self, client, admin_auth_headers):
        files = {"file": ("users.csv", BytesIO(b"email,name\na@b.com,A"), "text/csv")}
        response = client.post("/api/users/import-excel", files=files, headers=admin_auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "hỗ trợ" in response.json()["detail"].lower()

    def test_import_empty_file(self, client, admin_auth_headers):
        files = {"file": ("users.xlsx", BytesIO(b""), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/api/users/import-excel", files=files, headers=admin_auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_missing_email_header(self, client, admin_auth_headers):
        excel_data = create_excel_file(["full_name", "phone"], [["Nguyen Van A", "0901234567"]])
        files = {"file": ("users.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/api/users/import-excel", files=files, headers=admin_auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "thiếu cột" in response.json()["detail"].lower() or "email" in response.json()["detail"].lower()

    def test_import_success_all_valid(self, client, admin_auth_headers, db_session):
        headers = ["email", "full_name", "password", "role", "phone"]
        rows = [
            ["import_user1@example.com", "User One", "Pass@123", "TRAINEE", "0911111111"],
            ["import_user2@example.com", "User Two", "Pass@123", "TRAINER", "0922222222"],
            ["import_user3@example.com", "User Three", "Pass@123", "TRAINEE", "0933333333"],
        ]
        excel_data = create_excel_file(headers, rows)
        files = {"file": ("users.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/api/users/import-excel", files=files, headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_rows"] == 3
        assert data["success_count"] == 3
        assert data["failed_count"] == 0
        assert len(data["errors"]) == 0
        assert "import_user1@example.com" in data["imported_emails"]
        assert "import_user2@example.com" in data["imported_emails"]

        # Kiểm tra người dùng đã được tạo trong cơ sở dữ liệu
        u1 = db_session.query(User).filter(User.email == "import_user1@example.com").first()
        assert u1 is not None
        assert u1.full_name == "User One"
        assert u1.phone_number == "0911111111"

        u2 = db_session.query(User).filter(User.email == "import_user2@example.com").first()
        assert u2 is not None
        role_names = [r.name for r in u2.roles]
        assert "TRAINER" in role_names

    def test_import_partial_with_duplicates_and_invalid_email(self, client, admin_auth_headers, db_session):
        # Tạo sẵn 1 user trong DB để kiểm tra trùng email DB
        existing_user = User(
            email="existing_db@example.com",
            full_name="Existing DB User",
            password_hash="fake",
            is_active=True,
        )
        db_session.add(existing_user)
        db_session.commit()

        headers = ["email", "full_name"]
        rows = [
            ["valid_first@example.com", "First Valid"],
            ["invalid_email_format", "Invalid Email"],
            ["existing_db@example.com", "Duplicate DB Email"],
            ["duplicate_batch@example.com", "Batch Dup 1"],
            ["duplicate_batch@example.com", "Batch Dup 2"],
        ]
        excel_data = create_excel_file(headers, rows)
        files = {"file": ("users.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/api/users/import-excel", files=files, headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_rows"] == 5
        # valid_first và duplicate_batch (lần 1) thành công = 2
        assert data["success_count"] == 2
        # invalid_email, existing_db, duplicate_batch (lần 2) thất bại = 3
        assert data["failed_count"] == 3
        assert len(data["errors"]) == 3
