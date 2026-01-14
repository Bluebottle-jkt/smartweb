import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_login_success():
    """Test successful login with valid credentials."""
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.cookies.get("access_token") is not None


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_logout():
    """Test logout functionality."""
    response = client.post("/auth/logout")
    assert response.status_code == 200
