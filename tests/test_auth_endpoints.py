"""Tests for authentication and session management endpoints."""
import pytest
from starlette.testclient import TestClient
from backend.http.app import app
from backend.http.auth import seed_demo_users


@pytest.fixture(scope="module")
def client():
    seed_demo_users()
    return TestClient(app)


def test_sign_in_success(client):
    res = client.post(
        "/api/v1/auth/sign-in",
        json={"email": "admin@gecompose.internal", "password": "password123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "admin@gecompose.internal"
    assert data["role"] == "coordinator"
    assert data["token"] is not None
    assert "gc_session" in res.cookies


def test_sign_in_alias_and_reviewer(client):
    res = client.post(
        "/auth/sign-in",
        json={"email": "rao@gecompose.internal", "password": "password123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Prof. Rao"
    assert data["role"] == "reviewer"
    assert data["token"] is not None


def test_sign_in_invalid_credentials(client):
    res = client.post(
        "/auth/sign-in",
        json={"email": "admin@gecompose.internal", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_auth_me_bearer_token(client):
    # 1. Sign in
    sign_in_res = client.post(
        "/auth/sign-in",
        json={"email": "dean@gecompose.internal", "password": "password123"},
    )
    token = sign_in_res.json()["token"]

    # 2. Call /auth/me with Bearer token (no cookies)
    no_cookie_client = TestClient(app, cookies={})
    me_res = no_cookie_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["name"] == "Dean Academics"
    assert data["role"] == "reviewer"


def test_auth_me_unauthorized(client):
    no_cookie_client = TestClient(app, cookies={})
    res = no_cookie_client.get("/auth/me")
    assert res.status_code == 401


def test_sign_up_and_sign_out(client):
    import uuid
    random_email = f"user_{uuid.uuid4().hex[:8]}@gecompose.internal"
    
    # 1. Sign up
    up_res = client.post(
        "/auth/sign-up",
        json={"name": "New Scientist", "email": random_email, "password": "password123"},
    )
    assert up_res.status_code == 201
    user_data = up_res.json()
    token = user_data["token"]
    assert token is not None

    # 2. Check /auth/me
    test_client = TestClient(app, cookies={})
    me_res = test_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == random_email

    # 3. Sign out
    out_res = test_client.post("/auth/sign-out", headers={"Authorization": f"Bearer {token}"})
    assert out_res.status_code == 204

    # 4. Check /auth/me is now unauthorized
    me_after_res = test_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after_res.status_code == 401


def test_sign_up_duplicate_email(client):
    res = client.post(
        "/auth/sign-up",
        json={"name": "Duplicate", "email": "admin@gecompose.internal", "password": "password123"},
    )
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()
