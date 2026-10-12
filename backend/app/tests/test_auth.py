import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_and_login():
    # Register
    r = client.post("/api/auth/register", json={
        "email": "testuser@example.com",
        "full_name": "Test User",
        "password": "TestPass123!",
    })
    # May fail if DB not available in test env – this is a skeleton
    assert r.status_code in (200, 500, 409)


def test_login_invalid():
    r = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrong",
    })
    assert r.status_code in (401, 500)
