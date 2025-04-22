"""
Shared fixtures for unit tests
"""

import pytest

from cornflow_f.models.role import RoleModel
from cornflow_f.models.user import UserModel
from cornflow_f.tests.data.const import TEST_USER, TEST_ROLE


@pytest.fixture
def test_user(db_session):
    """
    Create a test user for authentication and other tests
    """
    user = UserModel(**TEST_USER)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """
    Get authentication headers for protected endpoints
    """
    response = client.post(
        "/login",
        json={"username": test_user.username, "password": TEST_USER["password"]},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_role(db_session):
    """
    Create a test role for role tests
    """
    role = RoleModel(**TEST_ROLE)
    db_session.add(role)
    db_session.commit()
    return role
