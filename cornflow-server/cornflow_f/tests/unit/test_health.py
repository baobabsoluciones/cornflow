from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """
    Test the root endpoint
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_hello_endpoint(client: TestClient):
    """
    Test the hello endpoint with a name parameter
    """
    name = "TestUser"
    response = client.get(f"/hello/{name}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Hello {name}"}


def test_db_endpoint(client: TestClient):
    """
    Test the database test endpoint
    """
    response = client.get("/db")
    assert response.status_code == 200
    assert response.json() == {"message": "Database connection successful"}
