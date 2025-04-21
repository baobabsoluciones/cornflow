from fastapi.testclient import TestClient
from cornflow_f.tests.data.const import (
    TEST_USER,
    TEST_USER_WEAK_PASSWORD,
    TEST_USER_DISPOSABLE_EMAIL,
    TEST_USER_DUPLICATE_USERNAME,
    TEST_USER_DUPLICATE_EMAIL,
)


def test_signup_success(client: TestClient):
    """
    Test successful user signup
    """
    response = client.post("/signup/", json=TEST_USER)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == TEST_USER["username"]
    assert data["email"] == TEST_USER["email"]
    assert "id" in data
    assert "password" not in data


def test_signup_weak_password(client: TestClient):
    """
    Test signup with weak password
    """
    response = client.post("/signup/", json=TEST_USER_WEAK_PASSWORD)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "password" in data["detail"].lower()


def test_signup_disposable_email(client: TestClient):
    """
    Test signup with disposable email
    """
    response = client.post("/signup/", json=TEST_USER_DISPOSABLE_EMAIL)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "disposable" in data["detail"].lower()


def test_signup_duplicate_username(client: TestClient):
    """
    Test signup with duplicate username
    """
    # First signup
    client.post("/signup/", json=TEST_USER)
    # Try to signup with same username
    response = client.post("/signup/", json=TEST_USER_DUPLICATE_USERNAME)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "username" in data["detail"].lower()


def test_signup_duplicate_email(client: TestClient):
    """
    Test signup with duplicate email
    """
    # First signup
    client.post("/signup/", json=TEST_USER)
    # Try to signup with same email
    response = client.post("/signup/", json=TEST_USER_DUPLICATE_EMAIL)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "email" in data["detail"].lower()
