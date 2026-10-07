import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


# Select a disposable database BEFORE importing the app. Existing SCRUM-29
# tests use SessionLocal directly and must never run against the user's database.
os.environ["DATABASE_URL"] = "sqlite://"

from app import database  # noqa: E402

database.engine.dispose()
database.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
database.SessionLocal.configure(bind=database.engine)


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    from app.database import SessionLocal
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.role_permission import RolePermission
    from app.routers import users

    with SessionLocal() as db:
        db.add_all([
            Role(role_id=1, role_name="ADMIN"),
            Role(role_id=2, role_name="INSTRUCTOR"),
            Role(role_id=3, role_name="STUDENT"),
            Role(role_id=4, role_name="ACCOUNTANT"),
            Role(role_id=5, role_name="TRAINING_MANAGER"),
            Role(role_id=6, role_name="ADMISSIONS"),
        ])
        db.add_all([
            Permission(permission_id=1, permission_name="USER_MANAGE"),
            Permission(permission_id=2, permission_name="ROLE_MANAGE"),
            Permission(permission_id=3, permission_name="CURRICULUM_MANAGE"),
            Permission(permission_id=4, permission_name="SUBJECT_MANAGE"),
            Permission(permission_id=5, permission_name="LEAD_MANAGE"),
        ])
        db.flush()
        db.add_all([
            RolePermission(role_id=1, permission_id=1),
            RolePermission(role_id=1, permission_id=2),
            RolePermission(role_id=1, permission_id=3),
            RolePermission(role_id=5, permission_id=3),
            RolePermission(role_id=1, permission_id=4),
            RolePermission(role_id=5, permission_id=4),
            RolePermission(role_id=1, permission_id=5),
            RolePermission(role_id=5, permission_id=5),
            RolePermission(role_id=6, permission_id=5),
        ])
        db.commit()

    async def skip_email(**kwargs):
        pass

    original = users.send_new_account_email
    users.send_new_account_email = skip_email
    yield
    users.send_new_account_email = original
    from app.database import engine
    engine.dispose()
