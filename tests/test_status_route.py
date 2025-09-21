from fastapi.testclient import TestClient
from srv.app import app

client = TestClient(app)


def test_status_410_route_is_gone():
    """Tests that the response returns a 410 status code and has the correct headers & text."""
    r = client.get("/status/some-id")
    assert r.status_code == 410
    assert "Deprecation" in r.headers
    assert r.headers.get("Deprecation") is not None and r.headers.get(
        "Deprecation") == "Sat, 30 Aug 2025 17:43:17 GMT"
    assert "Sunset" in r.headers
    assert r.headers.get("Sunset") is not None and r.headers.get(
        "Sunset") == "Sun, 21 Sep 2025 23:59:59 GMT"
    assert "has been retired" in r.text.lower()
