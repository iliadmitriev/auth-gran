import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app


@pytest.fixture(name="db_path", scope="session")
def db_path():
    return ":memory:"


@pytest.fixture(name="db", scope="session")
def db_fix(db_path):
    db_uri = f"sqlite:///{db_path}"

    engine = create_engine(
        db_uri,
        connect_args={"check_same_thread": False},
        echo=True,
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    db = TestingSessionLocal()
    Base.metadata.create_all(bind=db.connection().engine)

    yield db

    db.close()
    engine.dispose()


@pytest.fixture(name="client", scope="session")
def client_fix(db):
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)

    yield client

    client.close()


@pytest.fixture(name="user", scope="session")
def user_fix(db):
    user_data = {"email": "test@example.com", "password": "testpass"}

    hashed_password = get_password_hash(user_data["password"])
    db_user = User(
        is_active=True,
        is_admin=False,
        email=user_data["email"],
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()

    return user_data


@pytest.fixture(name="admin", scope="session")
def admin_fix(db):
    admin_data = {"email": "admin@example.com", "password": "adminpass"}

    hashed_password = get_password_hash(admin_data["password"])
    db_user = User(
        is_active=True,
        is_admin=False,
        email=admin_data["email"],
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()

    return admin_data


def test_register(client):
    response = client.post(
        "/v1/auth/register",
        json={"email": "new@example.com", "password": "newpass"},
    )
    assert response.status_code == 200
    assert "email" in response.json()
    assert response.json()["email"] == "new@example.com"


def test_login(user, client):
    response = client.post(
        "/v1/auth/login",
        data={"username": user["email"], "password": user["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(user, client):
    response = client.post(
        "/v1/auth/login",
        data={"username": user["email"], "password": "wrong"},
    )
    assert response.status_code == 401


def test_protected_route(user, client):
    # First login to get token
    login_response = client.post(
        "/v1/auth/login",
        data={"username": user["email"], "password": user["password"]},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Try to access protected route
    response = client.get(
        "/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should fail because user is not admin
    assert response.status_code == 403
