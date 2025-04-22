"""
Unit tests for role functionality
"""

from cornflow_f.tests.data.const import (
    TEST_ROLE,
    TEST_ROLE_DUPLICATE_NAME,
    INVALID_ROLE_NAME,
)

from cornflow_f.tests.fixtures import auth_headers, test_role, test_user


def test_get_roles_success(client, test_role, auth_headers):
    """
    Test successful retrieval of all roles
    """
    response = client.get("/roles", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == TEST_ROLE["name"]
    assert data[0]["description"] == TEST_ROLE["description"]


def test_get_roles_unauthorized(client):
    """
    Test getting roles without authentication
    """
    response = client.get("/roles")
    assert response.status_code == 401


def test_create_role_success(client, auth_headers):
    """
    Test successful role creation
    """
    response = client.post("/roles", json=TEST_ROLE, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == TEST_ROLE["name"]
    assert data["description"] == TEST_ROLE["description"]


def test_create_role_duplicate_name(client, test_role, auth_headers):
    """
    Test role creation with duplicate name
    """
    response = client.post(
        "/roles", json=TEST_ROLE_DUPLICATE_NAME, headers=auth_headers
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Role with this name already exists"


def test_create_role_invalid_data(client, auth_headers):
    """
    Test role creation with invalid data
    """
    response = client.post("/roles", json=INVALID_ROLE_NAME, headers=auth_headers)
    assert response.status_code == 422


def test_update_role_success(client, test_role, auth_headers):
    """
    Test successful role update
    """
    update_data = {"description": "Updated description"}

    response = client.patch(
        f"/roles/{test_role.id}", json=update_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == TEST_ROLE["name"]
    assert data["description"] == "Updated description"


def test_update_role_not_found(client, auth_headers):
    """
    Test updating non-existent role
    """
    update_data = {"description": "Updated description"}
    response = client.patch("/roles/999", json=update_data, headers=auth_headers)
    assert response.status_code == 404


def test_replace_role_success(client, test_role, auth_headers):
    """
    Test successful role replacement
    """
    replace_data = {"name": "new_role", "description": "New description"}
    response = client.put(
        f"/roles/{test_role.id}", json=replace_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "new_role"
    assert data["description"] == "New description"


def test_replace_role_not_found(client, auth_headers):
    """
    Test replacing non-existent role
    """
    replace_data = {"name": "new_role", "description": "New description"}
    response = client.put("/roles/999", json=replace_data, headers=auth_headers)
    assert response.status_code == 404


def test_delete_role_success(client, test_role, auth_headers):
    """
    Test successful role deletion
    """
    response = client.delete(f"/roles/{test_role.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify role is soft deleted
    response = client.get("/roles", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_delete_role_not_found(client, auth_headers):
    """
    Test deleting non-existent role
    """
    response = client.delete("/roles/999", headers=auth_headers)
    assert response.status_code == 404
