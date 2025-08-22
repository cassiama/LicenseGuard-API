import re
from datetime import date, datetime
from fastapi.testclient import TestClient
from srv.app import app
from srv.schemas import AnalyzeResult

client = TestClient(app)

HEX32 = re.compile(r"^[0-9a-f]{32}$")


def test_status_404_not_found(client_with_seed):
    r = client_with_seed.get("/status/does-not-exist")
    assert r.status_code == 404
    assert "not found" in r.text.lower()


def test_check_response_format_in_progress_without_result(client_with_seed):
    result = client_with_seed.get("/status/9c2a06a435814724a8994ec9b48ff4cd")
    assert result.status_code == 200, result.text
    body = result.json()
    
    # check response fields
    assert "project_id" in body and isinstance(body["project_id"], str)
    assert "status" in body and isinstance(body["status"], str)
    assert "result" in body and body["result"] is None
    assert "timestamp" in body and isinstance(body["timestamp"], str)
    


def test_status_200_in_progress_without_result(client_with_seed):
    result = client_with_seed.get("/status/9c2a06a435814724a8994ec9b48ff4cd")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["project_id"] == "9c2a06a435814724a8994ec9b48ff4cd"
    assert HEX32.match(body["project_id"])
    assert body["status"] == "in_progress"
    assert body["result"] is None


def test_check_response_format_completed_with_result(client_with_seed):
    result = client_with_seed.get("/status/776eaf11601c429783d23248b361d2b8")
    assert result.status_code == 200, result.text
    body = result.json()

    # check response fields
    assert "project_id" in body and isinstance(body["project_id"], str)
    assert "status" in body and isinstance(body["status"], str)
    assert "result" in body and isinstance(body["result"], dict)
    assert "timestamp" in body and isinstance(body["timestamp"], str)
    assert "project_name" in body["result"] and isinstance(body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                                "license", "confidence_score"}    


def test_status_200_completed_with_result(client_with_seed):
    result = client_with_seed.get("/status/776eaf11601c429783d23248b361d2b8")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["project_id"] == "776eaf11601c429783d23248b361d2b8"
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert body["result"]["project_name"] == "MyCoolCompleteProject"
    f = body["result"]["files"][0]
    assert f["name"] == "contourpy"
    assert f["version"] == "1.3.1"
    assert f["license"] == "BSD-3-Clause"
    assert f["confidence_score"] == 0.80
