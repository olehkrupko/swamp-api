from fastapi.testclient import TestClient
from run import app


client = TestClient(app)


def test_list_frequencies():
    response = client.get("/frequency/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
