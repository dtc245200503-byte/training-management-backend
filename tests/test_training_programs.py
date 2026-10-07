import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.core.security import create_access_token
from app.database import SessionLocal
from app.main import app
from app.migrations import ensure_training_program_columns, seed_training_program_permission
from app.models.training_program import TrainingClass, TrainingProgram
from app.models.user import User
from app.models.user_role import UserRole


@pytest.fixture
def context():
    prefix = "T32-" + uuid.uuid4().hex[:12].upper()
    users = []
    tokens = {}
    with SessionLocal() as db:
        for name, role_id in (("manager", 5), ("student", 3), ("instructor", 2), ("admin", 1)):
            user = User(username=prefix + name, full_name="Người dùng kiểm thử", email=prefix + name + "@example.com",
                        password="unused", role_id=role_id, is_locked=False)
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.user_id, role_id=role_id))
            users.append(user.user_id)
            # JWT role is intentionally not trusted for authorization.
            tokens[name] = {"Authorization": "Bearer " + create_access_token(user.user_id, "ADMIN")}
        db.commit()
    with TestClient(app) as client:
        ctx = {"client": client, "tokens": tokens, "prefix": prefix, "program_ids": [], "users": users}
        yield ctx
    with SessionLocal() as db:
        db.query(TrainingClass).filter(TrainingClass.course_id.in_(ctx["program_ids"])).delete(synchronize_session=False)
        db.query(TrainingProgram).filter(TrainingProgram.course_id.in_(ctx["program_ids"])).delete(synchronize_session=False)
        db.query(UserRole).filter(UserRole.user_id.in_(users)).delete(synchronize_session=False)
        db.query(User).filter(User.user_id.in_(users)).delete(synchronize_session=False)
        db.commit()


def payload(ctx, suffix="A", **updates):
    return {"code": ctx["prefix"] + suffix, "name": "Lập trình căn bản", "description": "Chương trình kiểm thử",
            "total_duration_hours": "40.50", "standard_tuition": "2500000", "status": "active", **updates}


def create(ctx, suffix="A", **updates):
    response = ctx["client"].post("/api/curriculums", headers=ctx["tokens"]["manager"], json=payload(ctx, suffix, **updates))
    if response.status_code == 201:
        ctx["program_ids"].append(response.json()["curriculum_id"])
    return response


def add_class(ctx, program_id, status="in_progress"):
    with SessionLocal() as db:
        item = TrainingClass(class_name="Lớp kiểm thử", course_id=program_id, status=status)
        db.add(item); db.commit(); db.refresh(item)
        return item.class_id


def test_manager_can_create_read_list_and_update_program(context):
    response = create(context, code="  " + context["prefix"].lower() + "  ", name="  Lập trình căn bản  ")
    assert response.status_code == 201
    item = response.json()
    assert item["code"] == context["prefix"]
    assert item["name"] == "Lập trình căn bản"
    assert item["total_duration_hours"] == "40.50"
    assert item["standard_tuition"] == "2500000"
    assert item["can_delete"] and item["active_class_count"] == 0
    client, headers, program_id = context["client"], context["tokens"]["manager"], item["curriculum_id"]
    assert client.get(f"/api/curriculums/{program_id}", headers=headers).json() == item
    result = client.get("/api/curriculums", headers=headers, params={"search": context["prefix"].lower()}).json()
    assert result["total"] == 1 and result["items"] == [item]
    updated = client.put(f"/api/curriculums/{program_id}", headers=headers,
                         json=payload(context, name="Chương trình mới", total_duration_hours="120", standard_tuition="0", description=" "))
    assert updated.status_code == 200
    assert updated.json()["name"] == "Chương trình mới" and updated.json()["description"] is None
    assert updated.json()["standard_tuition"] == "0"


def test_admin_can_manage_programs(context):
    response = context["client"].post("/api/curriculums", headers=context["tokens"]["admin"], json=payload(context))
    assert response.status_code == 201
    context["program_ids"].append(response.json()["curriculum_id"])


def test_duplicate_code_is_case_insensitive_and_update_is_atomic(context):
    first = create(context).json()
    duplicate = create(context, code=first["code"].lower())
    assert duplicate.status_code == 409 and "Mã chương trình" in duplicate.json()["detail"]
    second = create(context, "B").json()
    response = context["client"].put(f"/api/curriculums/{second['curriculum_id']}", headers=context["tokens"]["manager"],
                                     json=payload(context, code=first["code"], name="Không được lưu"))
    assert response.status_code == 409
    assert context["client"].get(f"/api/curriculums/{second['curriculum_id']}", headers=context["tokens"]["manager"]).json() == second


def test_database_also_enforces_unique_code(context):
    from sqlalchemy.exc import IntegrityError
    item = create(context).json()
    with SessionLocal() as db:
        db.add(TrainingProgram(course_name="Trùng mã", code=item["code"]))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()


@pytest.mark.parametrize("field,value", [
    ("code", ""), ("code", " "), ("code", "MÃ-ĐÀO-TẠO"), ("code", "ABC DEF"), ("code", "A" * 51),
    ("name", " "), ("name", "A" * 101), ("description", "A" * 5001),
    ("total_duration_hours", "0"), ("total_duration_hours", "-1"), ("total_duration_hours", "0.001"),
    ("total_duration_hours", "1000000"), ("total_duration_hours", "NaN"),
    ("standard_tuition", "-1"), ("standard_tuition", "1.5"), ("standard_tuition", "1000000000000"),
    ("standard_tuition", "Infinity"), ("status", "invalid"), ("status", None), ("curriculum_id", 999),
])
def test_invalid_program_data_is_rejected(context, field, value):
    assert create(context, **{field: value}).status_code == 422


def test_running_class_prevents_delete_even_after_deactivation(context):
    item = create(context).json()
    class_id = add_class(context, item["curriculum_id"])
    route = f"/api/curriculums/{item['curriculum_id']}"
    client, headers = context["client"], context["tokens"]["manager"]
    listed = client.get(route, headers=headers).json()
    assert listed["active_class_count"] == 1 and listed["total_class_count"] == 1 and not listed["can_delete"]
    response = client.delete(route, headers=headers)
    assert response.status_code == 409 and "ngừng áp dụng" in response.json()["detail"]
    disabled = client.patch(route + "/status", headers=headers, json={"status": "inactive"})
    assert disabled.status_code == 200 and disabled.json()["status"] == "inactive"
    assert client.delete(route, headers=headers).status_code == 409
    with SessionLocal() as db:
        assert db.get(TrainingClass, class_id).status == "in_progress"
        assert db.get(TrainingProgram, item["curriculum_id"]).deleted_at is None
    active = client.get("/api/curriculums", headers=headers, params={"status": "active", "search": context["prefix"]}).json()
    assert active["total"] == 0
    assert client.patch(route + "/status", headers=headers, json={"status": "active"}).status_code == 200


@pytest.mark.parametrize("class_status", [None, "completed", "cancelled"])
def test_delete_removes_from_catalog_without_erasing_class_history(context, class_status):
    item = create(context).json()
    class_id = add_class(context, item["curriculum_id"], class_status) if class_status else None
    route = f"/api/curriculums/{item['curriculum_id']}"
    client, headers = context["client"], context["tokens"]["manager"]
    assert client.delete(route, headers=headers).status_code == 200
    assert client.get(route, headers=headers).status_code == 404
    assert client.get("/api/curriculums", headers=headers, params={"search": context["prefix"]}).json()["total"] == 0
    assert client.patch(route + "/status", headers=headers, json={"status": "active"}).status_code == 404
    with SessionLocal() as db:
        assert db.get(TrainingProgram, item["curriculum_id"]).deleted_at is not None
        if class_id: assert db.get(TrainingClass, class_id).course_id == item["curriculum_id"]
    # Codes are reserved across history as well, avoiding ambiguous old class links.
    assert create(context).status_code == 409


def test_filter_search_and_pagination(context):
    create(context, "A", name="Chương trình Alpha")
    create(context, "B", status="inactive", name="Chương trình Beta")
    client, headers = context["client"], context["tokens"]["manager"]
    result = client.get("/api/curriculums", headers=headers, params={"search": context["prefix"], "page_size": 1}).json()
    assert result["total"] == 2 and len(result["items"]) == 1
    second = client.get("/api/curriculums", headers=headers, params={"search": context["prefix"], "page_size": 1, "page": 2}).json()
    assert second["items"][0]["curriculum_id"] != result["items"][0]["curriculum_id"]
    filtered = client.get("/api/curriculums", headers=headers, params={"search": context["prefix"], "status": "inactive"}).json()
    assert filtered["total"] == 1 and filtered["items"][0]["name"] == "Chương trình Beta"
    assert client.get("/api/curriculums", headers=headers, params={"search": "%"}).json()["total"] == 0


@pytest.mark.parametrize("role", ["student", "instructor", None])
@pytest.mark.parametrize("method,path", [("get", ""), ("post", ""), ("get", "/999"),
                                         ("put", "/999"), ("delete", "/999"), ("patch", "/999/status"),
                                         ("get", "/999/subjects")])
def test_all_routes_require_permission(context, role, method, path):
    kwargs = {"headers": context["tokens"][role]} if role else {}
    if method in ("post", "put"): kwargs["json"] = payload(context)
    if method == "patch": kwargs["json"] = {"status": "inactive"}
    response = getattr(context["client"], method)("/api/curriculums" + path, **kwargs)
    assert response.status_code in (401, 403)


def test_nonexistent_program_and_invalid_status(context):
    client, headers = context["client"], context["tokens"]["manager"]
    assert client.get("/api/curriculums/999999", headers=headers).status_code == 404
    assert client.delete("/api/curriculums/999999", headers=headers).status_code == 404
    assert client.patch("/api/curriculums/999999/status", headers=headers, json={"status": "invalid"}).status_code == 422
    assert client.get("/api/curriculums", headers=headers, params={"page": 0}).status_code == 422


def test_legacy_migration_is_idempotent_and_preserves_rows():
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE courses (course_id INTEGER PRIMARY KEY, course_name VARCHAR(100), description TEXT, duration_months INTEGER)"))
        c.execute(text("INSERT INTO courses VALUES (1, 'Chương trình cũ', 'Mô tả cũ', 3)"))
        c.execute(text("CREATE TABLE classes (class_id INTEGER PRIMARY KEY, course_id INTEGER, class_name VARCHAR(100))"))
        c.execute(text("INSERT INTO classes VALUES (1, 1, 'Lớp cũ')"))
    ensure_training_program_columns(engine)
    ensure_training_program_columns(engine)
    with engine.connect() as c:
        program = c.execute(text("SELECT course_name, description, duration_months, code, total_duration_hours, standard_tuition, status FROM courses")).one()
        assert program == ("Chương trình cũ", "Mô tả cũ", 3, "CT-1", 0, 0, "active")
        assert c.execute(text("SELECT course_id, class_name, status FROM classes")).one() == (1, "Lớp cũ", "in_progress")
    assert any(item.get("unique") and item["column_names"] == ["code"] for item in inspect(engine).get_indexes("courses"))
    engine.dispose()


def test_permission_seed_does_not_regrant_revoked_permissions(context):
    from app.models.permission import Permission
    from app.models.role_permission import RolePermission
    with SessionLocal() as db:
        permission = db.query(Permission).filter_by(permission_name="CURRICULUM_MANAGE").one()
        existing = db.query(RolePermission).filter_by(role_id=5, permission_id=permission.permission_id).one()
        db.delete(existing); db.commit()
        seed_training_program_permission()
        assert db.query(RolePermission).filter_by(role_id=5, permission_id=permission.permission_id).first() is None
        db.add(RolePermission(role_id=5, permission_id=permission.permission_id)); db.commit()
