import pytest
from fastapi import status
from conftest import HEX32


def test_check_response_format(post_file):
    """Tests the format of the "POST /analyze" response."""
    r = post_file(
        "requirements.txt",
        b"requests==2.32.3\n",
        "text/plain",
    )
    assert r.status_code == 200
    body = r.json()

    # check response fields
    assert "project_id" in body and isinstance(body["project_id"], str)
    assert "status" in body and isinstance(body["status"], str)
    assert "result" in body and body["result"] is not None


def test_accepts_valid_requirements_txt_minimal(post_file):
    """Tests that a minimal requirements.txt with basic packages is accepted."""
    r = post_file(
        "requirements.txt",
        b"requests==2.32.3\nfastapi>=0.110\n",
        "text/plain",
        # default project_name
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert "project_name" in body["result"] and isinstance(
        body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(
        body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(
        body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                             "license", "confidence_score"}


def test_rejects_non_string_project_name(post_file):
    """Tests that a project name which is not a string results in a 422 error."""
    invalid_name = dict()  # using a dict (which isn't implicitly casted to a str by FastAPI) instead of a string
    with pytest.raises(TypeError) as ex:
        post_file(
            "requirements.txt",
            b"requests==2.32.3\n",
            "text/plain",
            form={"project_name": invalid_name},
        )
    assert "invalid type for value" in str(ex.value).lower()


def test_rejects_project_name_too_short(post_file):
    """Tests that a project name shorter than 1 character results in a 422 error."""
    invalid_name = ""  # too short!
    r = post_file(
        "requirements.txt",
        b"requests==2.32.3\n",
        "text/plain",
        form={"project_name": invalid_name},
    )
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "project name must be between 1 and 100 characters" in r.text.lower()


def test_rejects_project_name_too_long(post_file):
    """Tests that a project name longer than 100 characters results in a 422 error."""
    invalid_name = "a" * 101  # too long!
    r = post_file(
        "requirements.txt",
        b"requests==2.32.3\n",
        "text/plain",
        form={"project_name": invalid_name},
    )
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "project name must be between 1 and 100 characters" in r.text.lower()


def test_llm_failure_handling(post_file, fake_llm):
    """Tests that the application correctly handles an LLM failure."""
    fake_llm._raise = True

    r = post_file(
        "requirements.txt",
        b"requests==2.32.3\n",
        "text/plain",
    )

    assert r.status_code == 200
    body = r.json()

    assert HEX32.match(body["project_id"])
    assert body["status"] == "failed"
    assert body["result"] is None


def test_accepts_valid_requirements_txt_unicode(post_file):
    """Tests that Unicode content in requirements.txt file is handled correctly."""
    content = "# コメント\nscikit-learn==1.7.1\n# más comentarios\n".encode(
        "utf-8")
    r = post_file(
        "requirements.txt",
        content,
        "text/plain"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert "project_name" in body["result"] and isinstance(
        body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(
        body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(
        body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                             "license", "confidence_score"}


def test_accepts_valid_requirements_txt_complex(post_file):
    """Tests a complex requirements.txt file with various formats and comments."""
    r = post_file(
        "requirements.txt",
        b"""
        # Development dependencies
        pytest>=7.0.0
        black==23.1.0
        
        # Runtime dependencies
        fastapi>=0.95.0
        pydantic[email]>=2.0.0
        SQLAlchemy==2.0.0
        
        # Optional extras
        uvicorn[standard]>=0.20.0; python_version >= "3.8"
        """,
        "text/plain"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert "project_name" in body["result"] and isinstance(
        body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(
        body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(
        body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                             "license", "confidence_score"}


def test_accepts_valid_with_charset_param_on_content_type(post_file):
    """Tests that the requirements.txt file is accepted when the content type specifies a charset."""
    r = post_file(
        "requirements.txt",
        "uvicorn[standard]==0.30.0\n".encode("utf-8"),
        "text/plain; charset=utf-8",  # validator splits before ';'
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert "project_name" in body["result"] and isinstance(
        body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(
        body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(
        body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                             "license", "confidence_score"}


def test_accepts_valid_with_project_name_form_field(post_file):
    """Tests that the project_name form field is accepted and used correctly."""
    r = post_file(
        "requirements.txt",
        b"requests==2.32.3\n",
        "text/plain",
        # custom name sent as multipart form field
        form={"project_name": "MyCustomProject"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert "project_name" in body["result"] and isinstance(
        body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(
        body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(
        body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                             "license", "confidence_score"}


def test_accepts_file_with_editable_and_named_entries(post_file):
    """Tests that a requirements.txt file with editable installs is accepted, while named entries are kept."""
    r = post_file(
        "requirements.txt",
        # -e (editable) lines are skipped while named entries are kept
        b"-e .[all]\nfastapi>=0.110\n",
        "text/plain"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert "project_name" in body["result"] and isinstance(
        body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(
        body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(
        body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                             "license", "confidence_score"}


def test_accepts_file_with_include_and_named_entries(post_file):
    """Tests that a requirements.txt file with include directives is accepted, while named entries are kept."""
    r = post_file(
        "requirements.txt",
        # -r (include) lines are skipped while named entries are kept
        b"-r requirements-dev.txt\nrequests==2.32.3\n",
        "text/plain"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert "project_name" in body["result"] and isinstance(
        body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(
        body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(
        body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                             "license", "confidence_score"}


def test_accepts_pep508_direct_url_line(post_file):
    """Tests that a requirements.txt file with a PEP 508 direct URL is accepted."""
    r = post_file(
        "requirements.txt",
        # 'name @ URL' is valid PEP 508 and should pass through
        b"urllib3 @ https://github.com/urllib3/urllib3/archive/refs/tags/1.26.8.zip\n",
        "text/plain"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert HEX32.match(body["project_id"])
    assert body["status"] == "completed"
    assert "project_name" in body["result"] and isinstance(
        body["result"]["project_name"], str)
    assert "analysis_date" in body["result"] and isinstance(
        body["result"]["analysis_date"], str)
    assert "files" in body["result"] and isinstance(
        body["result"]["files"], list)
    f = body["result"]["files"][0]
    assert set(f.keys()) >= {"name", "version",
                             "license", "confidence_score"}


def test_rejects_wrong_media_type_even_if_txt_extension(post_file):
    """Tests that a non-text media type results in a 415 error, even if the filename has a .txt extension."""
    r = post_file(
        "requirements.txt",
        b"anyio>=4.0.0",
        "application/json",  # wrong content type
    )
    assert r.status_code == 415
    assert "upload a text/plain requirements.txt file" in r.text.lower()


def test_rejects_wrong_extension_even_if_media_type_ok(post_file):
    """Tests that a wrong file extension results in a 422 error, even if the content type is correct."""
    # NOTE: this test is necessary because a client could lie about the extension even if the MIME type is correct
    r = post_file(
        "image.png",    # wrong file extension
        b"requests==2.32.3\n",
        "text/plain"
    )
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "file must have .txt extension" in r.text.lower()


def test_rejects_empty_file(post_file):
    """Tests that an empty requirements.txt file results in a 400 error."""
    r = post_file("requirements.txt", b"", "text/plain")
    assert r.status_code == 400
    assert "file is empty" in r.text.lower()


def test_rejects_comments_only(post_file):
    """Tests that a requirements.txt file containing only comments results in a 422 error."""
    content = b"# just a comment\n   \n# another comment"
    r = post_file("requirements.txt", content, "text/plain")
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "no requirements found" in r.text.lower()


def test_rejects_invalid_requirement_lines_single(post_file):
    """Tests that a requirements.txt file with a completely invalid line triggers a 422 error."""
    r = post_file(
        "requirements.txt",
        b"this is not valid!!!\n",  # a completely invalid line triggers a HTTP 422
        "text/plain"
    )
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "invalid requirements.txt file" in r.text.lower()


def test_rejects_invalid_requirement_lines_mixed_list(post_file):
    """Tests that a requirements.txt file with a mix of valid and invalid lines triggers a 422 error."""
    r = post_file(
        "requirements.txt",
        b"""
        requests==2.32.3
        invalid line !!!
        fastapi >= 0.110
        """,    # a mix of valid & invalid lines typically triggers a HTTP 422 from the parser
        "text/plain"
    )
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "invalid requirements.txt file" in r.text.lower()


def test_missing_file_param_triggers_422_from_fastapi(client):
    """Tests that missing the 'files' field in the request body triggers a 422 error."""
    # if no 'files' field is passed in, then FastAPI's validation layer should automatically throw a HTTP 422
    r = client.post("/analyze")
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
