import re
from fastapi.testclient import TestClient


HEX32 = re.compile(r"^[0-9a-f]{32}$")


def test_accepts_valid_requirements_txt_minimal(post_file):
    resp = post_file(
        "requirements.txt",
        b"requests==2.32.3\nfastapi>=0.110\n",
        "text/plain",
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["result"] is None
    assert HEX32.match(body["project_id"])


def test_accepts_valid_with_charset_param_on_content_type(post_file):
    resp = post_file(
        "requirements.txt",
        "uvicorn[standard]==0.30.0\n".encode("utf-8"),
        "text/plain; charset=utf-8",  # validator splits before ';'
    )
    assert resp.status_code == 202, resp.text


def test_rejects_wrong_media_type_even_if_txt_extension(post_file):
    resp = post_file(
        "requirements.txt",
        b"anyio>=4.0.0",
        "application/json",  # wrong content type
    )
    assert resp.status_code == 415
    assert "text/plain" in resp.text.lower()


def test_rejects_wrong_extension_even_if_media_type_ok(post_file):
    resp = post_file(
        "not_text.bin",  # wrong extension
        b"pydantic>=2.8.0",
        "text/plain",
    )
    assert resp.status_code == 422
    assert "extension" in resp.text.lower()


def test_rejects_empty_file(post_file):
    resp = post_file("requirements.txt", b"", "text/plain")
    assert resp.status_code == 400
    assert "empty" in resp.text.lower()


def test_rejects_comments_only(post_file):
    content = b"# just a comment\n   \n# another comment"
    resp = post_file("requirements.txt", content, "text/plain")
    assert resp.status_code == 422
    assert "no requirements" in resp.text.lower()


def test_rejects_invalid_requirement_lines_single(post_file):
    # with "requirements-parser", a completely invalid line triggers a HTTP 422
    content = b"this is not valid!!!\n"
    resp = post_file("requirements.txt", content, "text/plain")
    assert resp.status_code == 422
    assert "invalid requirements.txt file" in resp.text.lower()


def test_rejects_invalid_requirement_lines_mixed_list(post_file):
    # a mix of valid & invalid lines typically triggers a HTTP 422 from the parser
    content = b"""
    requests==2.32.3
    invalid line !!!
    fastapi >= 0.110
    """
    resp = post_file("requirements.txt", content, "text/plain")
    assert resp.status_code == 422
    assert "invalid requirements.txt file" in resp.text.lower()


def test_missing_file_param_triggers_422_from_fastapi(client):
    # if no 'files' field is passed in, then FastAPI's validation layer should automatically throw a HTTP 422
    resp = client.post("/analyze")
    assert resp.status_code == 422


def test_non_txt_filename_but_correct_content_type(post_file):
    # a client could lie about the extension even if the MIME type is correct
    resp = post_file("image.png", b"requests==2.32.3\n", "text/plain")
    assert resp.status_code == 422


def test_accepts_file_with_editable_and_named_entries(post_file):
    # -e (editable) lines are skipped by the dedicated parser while named entries are kept. thus, it's still a HTTP 202
    content = b"-e .[all]\nfastapi>=0.110\n"
    resp = post_file("requirements.txt", content, "text/plain")
    assert resp.status_code == 202, resp.text


def test_accepts_file_with_include_and_named_entries(post_file):
    # -r (include) lines are skipped by the dedicated parser while named entries are kept. thus, it's still a HTTP 202
    content = b"-r requirements-dev.txt\nrequests==2.32.3\n"
    resp = post_file("requirements.txt", content, "text/plain")
    assert resp.status_code == 202


def test_accepts_pep508_direct_url_line(post_file):
    # 'name @ URL' is valid PEP 508 and should pass through
    content = b"urllib3 @ https://github.com/urllib3/urllib3/archive/refs/tags/1.26.8.zip\n"
    resp = post_file("requirements.txt", content, "text/plain")
    assert resp.status_code == 202, resp.text
