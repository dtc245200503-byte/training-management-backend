import pytest
from fastapi import status


class TestAttachSubjectsS2_06:
    def test_attach_subject_unauthenticated(self, client):
        response = client.post("/api/training-programs/1/subjects", json={"subject_id": 1})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_attach_subject_forbidden_trainee(self, client, trainee_auth_headers):
        response = client.post("/api/training-programs/1/subjects", json={"subject_id": 1}, headers=trainee_auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_attach_and_list_and_detach_flow(self, client, admin_auth_headers):
        # 1. Tạo 1 Program
        prog_res = client.post(
            "/api/training-programs",
            json={"code": "PROG-ATTACH", "name": "Program for Attach Test"},
            headers=admin_auth_headers,
        )
        assert prog_res.status_code == status.HTTP_201_CREATED
        prog_id = prog_res.json()["id"]

        # 2. Tạo 2 Subjects
        sub1_res = client.post(
            "/api/subjects",
            json={"code": "SUB-ATT-1", "name": "Subject 1"},
            headers=admin_auth_headers,
        )
        sub1_id = sub1_res.json()["id"]

        sub2_res = client.post(
            "/api/subjects",
            json={"code": "SUB-ATT-2", "name": "Subject 2"},
            headers=admin_auth_headers,
        )
        sub2_id = sub2_res.json()["id"]

        # 3. Gắn sub1 với order_index = 1
        att1 = client.post(
            f"/api/training-programs/{prog_id}/subjects",
            json={"subject_id": sub1_id, "order_index": 1},
            headers=admin_auth_headers,
        )
        assert att1.status_code == status.HTTP_200_OK

        # 4. Gắn lại sub1 -> Phải báo lỗi 400 (đã tồn tại)
        dup_att = client.post(
            f"/api/training-programs/{prog_id}/subjects",
            json={"subject_id": sub1_id, "order_index": 1},
            headers=admin_auth_headers,
        )
        assert dup_att.status_code == status.HTTP_400_BAD_REQUEST

        # 5. Gắn sub2 với order_index = 2
        att2 = client.post(
            f"/api/training-programs/{prog_id}/subjects",
            json={"subject_id": sub2_id, "order_index": 2},
            headers=admin_auth_headers,
        )
        assert att2.status_code == status.HTTP_200_OK

        # 6. Xem danh sách môn học đã gắn
        list_res = client.get(f"/api/training-programs/{prog_id}/subjects", headers=admin_auth_headers)
        assert list_res.status_code == status.HTTP_200_OK
        data = list_res.json()
        assert len(data) == 2
        assert data[0]["subject_id"] == sub1_id
        assert data[0]["subject"]["code"] == "SUB-ATT-1"
        assert data[1]["subject_id"] == sub2_id

        # 7. Gỡ bỏ sub1 khỏi program
        detach_res = client.delete(f"/api/training-programs/{prog_id}/subjects/{sub1_id}", headers=admin_auth_headers)
        assert detach_res.status_code == status.HTTP_200_OK

        # 8. Xem lại danh sách, chỉ còn sub2
        list_res2 = client.get(f"/api/training-programs/{prog_id}/subjects", headers=admin_auth_headers)
        assert list_res2.status_code == status.HTTP_200_OK
        data2 = list_res2.json()
        assert len(data2) == 1
        assert data2[0]["subject_id"] == sub2_id

        # 9. Gỡ bỏ lại sub1 đã bị gỡ -> 404
        detach_again = client.delete(f"/api/training-programs/{prog_id}/subjects/{sub1_id}", headers=admin_auth_headers)
        assert detach_again.status_code == status.HTTP_404_NOT_FOUND
