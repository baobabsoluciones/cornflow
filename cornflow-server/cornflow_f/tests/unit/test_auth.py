"""
Unit tests for authentication functionality
"""

import pytest
from cornflow_f.models.user import UserModel
from cornflow_f.security import get_password_hash


@pytest.fixture
def test_user(db_session):
    """
    Create a test user for authentication tests
    """
    user = UserModel(
        username="testuser",
        email="test@example.com",
        password=get_password_hash("TestPass123!"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_login_success(client, test_user):
    """
    Test successful login with correct credentials
    """
    response = client.post(
        "/login/", json={"username": "testuser", "password": "TestPass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    """
    Test login with incorrect password
    """
    response = client.post(
        "/login/", json={"username": "testuser", "password": "WrongPass123!"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_nonexistent_user(client):
    """
    Test login with non-existent username
    """
    response = client.post(
        "/login/", json={"username": "nonexistent", "password": "TestPass123!"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_missing_fields(client):
    """
    Test login with missing required fields
    """
    # Test missing username
    response = client.post("/login/", json={"password": "TestPass123!"})
    assert response.status_code == 422

    # Test missing password
    response = client.post("/login/", json={"username": "testuser"})
    assert response.status_code == 422

    # Test empty request body
    response = client.post("/login/", json={})
    assert response.status_code == 422


def test_login_empty_fields(client):
    """
    Test login with empty fields
    """
    response = client.post("/login/", json={"username": "", "password": ""})
    assert response.status_code == 422
