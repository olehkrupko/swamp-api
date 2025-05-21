from fastapi.testclient import TestClient
from run import app


client = TestClient(app)


def test_list_feeds():
    response = client.get("/feeds/")
    assert response.status_code == 200
    assert isinstance(response.json(), list) or isinstance(response.json(), dict)


def test_explain_feed():
    response = client.get("/feeds/parse/?href=https://example.com")
    assert response.status_code in (200, 422)


def test_create_read_update_delete_feed():
    # Create
    feed_data = {
        "title": "Test Feed",
        "href": "https://test.com",
        "href_user": "https://test.com/user",
        "private": False,
        "frequency": "WEEKS",
        "notes": "Test notes",
        "json": {},
    }
    response = client.put("/feeds/", json=feed_data)
    assert response.status_code == 200
    feed = response.json()
    assert feed["title"] == feed_data["title"]
    feed_id = feed["_id"]

    # Read
    response = client.get(f"/feeds/{feed_id}/")
    assert response.status_code == 200
    assert response.json()["_id"] == feed_id

    # Update
    update_data = {"notes": "Updated notes"}
    response = client.put(f"/feeds/{feed_id}/", json=update_data)
    assert response.status_code == 200
    assert response.json()["notes"] == "Updated notes"

    # Delete
    response = client.delete(f"/feeds/{feed_id}/")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_push_updates():
    # Create feed first
    feed_data = {
        "title": "Push Feed",
        "href": "https://push.com",
        "href_user": "https://push.com/user",
        "private": False,
        "frequency": "WEEKS",
        "notes": "Push notes",
        "json": {},
    }
    response = client.put("/feeds/", json=feed_data)
    assert response.status_code == 200
    feed_id = response.json()["_id"]

    # Push updates
    updates = [
        {
            "name": "Update 1",
            "datetime": "2025-05-22T12:00:00+00:00",
            "href": "https://push.com/update1",
        },
        {
            "name": "Update 2",
            "datetime": "2025-05-22T13:00:00+00:00",
            "href": "https://push.com/update2",
        },
    ]
    response = client.post(f"/feeds/{feed_id}/", json={"updates": updates})
    assert response.status_code in (200, 422)
    # Clean up
    client.delete(f"/feeds/{feed_id}/")
