from fastapi.testclient import TestClient
from run import app


client = TestClient(app)


def test_list_updates():
    response = client.get("/updates/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    response = client.get("/updates/", params={"limit": 10})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 10

    response = client.get("/updates/", params={"private": True})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    for item in response.json():
        assert item["feed_data"]["private"] is True

    response = client.get("/updates/", params={"private": False})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    for item in response.json():
        assert item["feed_data"]["private"] is False

    response = client.get("/updates/", params={"_id": 3659})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    for item in response.json():
        assert item["feed_id"] == 3659
        assert item["feed_data"]["_id"] == 3659


def test_parse_updates():
    response = client.get("/updates/parse/?href=https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw/videos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # assert response.status_code in (200, 422)

    # response = client.get("/updates/parse/?href=https://example.com")
    # assert response.status_code == 422
    # assert isinstance(response.json(), list)
