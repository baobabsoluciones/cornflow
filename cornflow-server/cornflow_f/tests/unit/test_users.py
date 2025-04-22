import pytest
from fastapi.testclient import TestClient

from cornflow_f.models.user import UserModel
from cornflow_f.security import get_password_hash
from cornflow_f.tests.data.const import (
    TEST_USER,
    TEST_USER_WEAK_PASSWORD,
    TEST_USER_DISPOSABLE_EMAIL,
    TEST_USER_DUPLICATE_USERNAME,
    TEST_USER_DUPLICATE_EMAIL,
)
from cornflow_f.tests.unit.fixtures import test_user, auth_headers


def test_signup_success(client: TestClient):
    """
    Test successful user signup
    """
    response = client.post("/signup", json=TEST_USER)
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
    response = client.post("/signup", json=TEST_USER_WEAK_PASSWORD)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "password" in data["detail"].lower()


def test_signup_disposable_email(client: TestClient):
    """
    Test signup with disposable email
    """
    response = client.post("/signup", json=TEST_USER_DISPOSABLE_EMAIL)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "disposable" in data["detail"].lower()


def test_signup_duplicate_username(client: TestClient):
    """
    Test signup with duplicate username
    """
    # First signup
    client.post("/signup", json=TEST_USER)
    # Try to signup with same username
    response = client.post("/signup", json=TEST_USER_DUPLICATE_USERNAME)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "username" in data["detail"].lower()


def test_signup_duplicate_email(client: TestClient):
    """
    Test signup with duplicate email
    """
    # First signup
    client.post("/signup", json=TEST_USER)
    # Try to signup with same email
    response = client.post("/signup", json=TEST_USER_DUPLICATE_EMAIL)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "email" in data["detail"].lower()


def test_update_profile_success(client, test_user, auth_headers):
    """
    Test successful profile update
    """
    response = client.patch(
        f"/user/{test_user.uuid}",
        headers=auth_headers,
        json={
            "username": "newusername",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "Name",
            "password": "NewPass123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newusername"
    assert data["email"] == "new@example.com"
    assert data["first_name"] == "New"
    assert data["last_name"] == "Name"

    # Verify password change
    response = client.post(
        "/login", json={"username": "newusername", "password": "NewPass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.uuid


def test_update_profile_unauthorized(client, test_user):
    """
    Test profile update without authentication
    """
    response = client.patch(f"/user/{test_user.uuid}", json={"username": "newusername"})
    assert response.status_code == 401


def test_update_profile_invalid_token(client, test_user):
    """
    Test profile update with invalid token
    """
    # Create an invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token"}

    response = client.patch(
        f"/user/{test_user.uuid}",
        headers=invalid_headers,
        json={"username": "newusername"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_update_profile_wrong_user(client, test_user, auth_headers, db_session):
    """
    Test profile update for a different user
    """
    # Create another user
    other_user = UserModel(
        username="otheruser",
        email="other@example.com",
        password="OtherPass123!",
        first_name="Other",
        last_name="User",
    )
    db_session.add(other_user)
    db_session.commit()

    # Try to update other user's profile
    response = client.patch(
        f"/user/{other_user.uuid}",
        headers=auth_headers,
        json={"username": "newusername"},
    )
    assert response.status_code == 403


def test_update_profile_duplicate_username(client, test_user, auth_headers, db_session):
    """
    Test profile update with duplicate username
    """
    # Create another user
    other_user = UserModel(
        username="otheruser",
        email="other@example.com",
        password="OtherPass123!",
        first_name="Other",
        last_name="User",
    )
    db_session.add(other_user)
    db_session.commit()

    # Try to update username to existing one
    response = client.patch(
        f"/user/{test_user.uuid}", headers=auth_headers, json={"username": "otheruser"}
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


def test_update_profile_duplicate_email(client, test_user, auth_headers, db_session):
    """
    Test profile update with duplicate email
    """
    # Create another user
    other_user = UserModel(
        username="otheruser",
        email="other@example.com",
        password="OtherPass123!",
        first_name="Other",
        last_name="User",
    )
    db_session.add(other_user)
    db_session.commit()

    # Try to update email to existing one
    response = client.patch(
        f"/user/{test_user.uuid}",
        headers=auth_headers,
        json={"email": "other@example.com"},
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_update_profile_invalid_password(client, test_user, auth_headers):
    """
    Test profile update with invalid password
    """
    response = client.patch(
        f"/user/{test_user.uuid}", headers=auth_headers, json={"password": "weak"}
    )
    assert response.status_code == 400
    assert "Password must be at least 8 characters long" in response.json()["detail"]


def test_update_profile_disposable_email(client, test_user, auth_headers):
    """
    Test profile update with disposable email
    """
    response = client.patch(
        f"/user/{test_user.uuid}",
        headers=auth_headers,
        json={"email": "test@temp-mail.com"},
    )
    assert response.status_code == 400
    assert "Disposable email addresses are not allowed" in response.json()["detail"]


def test_get_all_users(client, test_user, auth_headers, db_session):
    """
    Test retrieving all users
    """
    # Create additional users for testing
    user1 = UserModel(
        username="user1",
        email="user1@example.com",
        password="User1Pass123!",
        first_name="User",
        last_name="One",
    )
    db_session.add(user1)

    user2 = UserModel(
        username="user2",
        email="user2@example.com",
        password="User2Pass123!",
        first_name="User",
        last_name="Two",
    )
    db_session.add(user2)

    db_session.commit()

    # Test getting all users
    response = client.get("/users", headers=auth_headers)
    assert response.status_code == 200

    # Verify response contains all users
    data = response.json()
    assert len(data) >= 3  # At least the test_user and the two we just created

    # Check that our test users are in the response
    usernames = [user["username"] for user in data]
    assert test_user.username in usernames
    assert "user1" in usernames
    assert "user2" in usernames

    # Verify the structure of the response
    for user in data:
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "first_name" in user
        assert "last_name" in user
