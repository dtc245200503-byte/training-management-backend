import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.init_db import seed_roles_and_permissions
from app.main import app
from app.models import RefreshToken, Role, User
from app.security.jwt import create_access_token
from app.security.password import hash_password

# Dùng SQLite in-memory cho testing để cách ly hoàn toàn
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Khởi tạo roles và permissions sẵn cho môi trường test
    seed_roles_and_permissions(db)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(
        email="user@example.com",
        password_hash=hash_password("password123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def inactive_user(db_session):
    user = User(
        email="inactive@example.com",
        password_hash=hash_password("password123"),
        full_name="Inactive User",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(db_session):
    role_admin = db_session.query(Role).filter(Role.name == "ADMIN").first()
    user = User(
        email="admin_test@example.com",
        password_hash=hash_password("password123"),
        full_name="Admin Test",
        is_active=True,
        is_locked=False,
        roles=[role_admin] if role_admin else [],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def trainer_user(db_session):
    role_trainer = db_session.query(Role).filter(Role.name == "TRAINER").first()
    user = User(
        email="trainer_test@example.com",
        password_hash=hash_password("password123"),
        full_name="Trainer Test",
        is_active=True,
        is_locked=False,
        roles=[role_trainer] if role_trainer else [],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def trainee_user(db_session):
    role_trainee = db_session.query(Role).filter(Role.name == "TRAINEE").first()
    user = User(
        email="trainee_test@example.com",
        password_hash=hash_password("password123"),
        full_name="Trainee Test",
        is_active=True,
        is_locked=False,
        roles=[role_trainee] if role_trainee else [],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def locked_user(db_session):
    role_trainee = db_session.query(Role).filter(Role.name == "TRAINEE").first()
    user = User(
        email="locked_test@example.com",
        password_hash=hash_password("password123"),
        full_name="Locked Test",
        is_active=True,
        is_locked=True,
        lock_reason="Vi phạm quy định",
        roles=[role_trainee] if role_trainee else [],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_auth_headers(admin_user):
    token = create_access_token({"sub": str(admin_user.id), "email": admin_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def trainer_auth_headers(trainer_user):
    token = create_access_token({"sub": str(trainer_user.id), "email": trainer_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def trainee_auth_headers(trainee_user):
    token = create_access_token({"sub": str(trainee_user.id), "email": trainee_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def locked_auth_headers(locked_user):
    token = create_access_token({"sub": str(locked_user.id), "email": locked_user.email})
    return {"Authorization": f"Bearer {token}"}
