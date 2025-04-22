from fastapi.testclient import TestClient


def test_db_endpoint(client: TestClient):
    """
    Test the database test endpoint
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"cornflow_status": "healthy"}
