import re
from fastapi.testclient import TestClient
from srv.app import app

client = TestClient(app)

HEX32 = re.compile(r"^[0-9a-f]{32}$")


def test_status_404_not_found(client_with_seed):
    r = client_with_seed.get("/status/does-not-exist")
    assert r.status_code == 404
    assert "not found" in r.text.lower()

def test_status_200_in_progress_without_result(client_with_seed):
    result = client_with_seed.get("/status/abc123abc123abc123abc123abc123ab")
    assert result.status_code == 200, result.text
    json_obj = result.json()
    assert json_obj["project_id"] == "abc123abc123abc123abc123abc123ab"
    assert json_obj["status"] == "in_progress"
    assert json_obj["result"] is None
    # timestamp exists and is ISO-like
    assert "timestamp" in json_obj and isinstance(json_obj["timestamp"], str)

def test_status_200_completed_with_result(client_with_seed):
    result = client_with_seed.get("/status/deadbeefdeadbeefdeadbeefdeadbeef")
    assert result.status_code == 200, result.text
    json_obj = result.json()
    assert json_obj["status"] == "completed"
    assert json_obj["result"]["project_name"] == "MyCoolCompleteProject"
    assert isinstance(json_obj["result"]["files"], list) and json_obj["result"]["files"]
    one = json_obj["result"]["files"][0]
    assert set(one.keys()) >= {"name", "version", "license", "confidence_score"}
