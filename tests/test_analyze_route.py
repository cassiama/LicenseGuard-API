from conftest import HEX32


def test_check_response_format(post_file):
    """Tests the format of the "POST /analyze" response."""
    resp = post_file(
        "requirements.txt",
        b"requests==2.32.3\n",
        "text/plain",
    )
    assert resp.status_code == 200
    body = resp.json()

    # check response fields
    assert "project_id" in body and isinstance(body["project_id"], str)
    assert "status" in body and isinstance(body["status"], str)
    assert "result" in body and body["result"] is not None


def test_accepts_valid_requirements_txt_minimal(post_file):
    """Tests that a minimal requirements.txt with basic packages is accepted."""
    resp = post_file(
        "requirements.txt",
        b"requests==2.32.3\nfastapi>=0.110\n",
        "text/plain",
        # default project_name
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
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


def test_llm_failure_handling(post_file, fake_llm):
    """Tests that the application correctly handles an LLM failure."""
    fake_llm._raise = True

    resp = post_file(
        "requirements.txt",
        b"requests==2.32.3\n",
        "text/plain",
    )

    assert resp.status_code == 200
    body = resp.json()

    assert HEX32.match(body["project_id"])
    assert body["status"] == "failed"
    assert body["result"] is None


def test_accepts_valid_requirements_txt_unicode(post_file):
    """Tests that Unicode content in requirements.txt file is handled correctly."""
    content = "# コメント\nscikit-learn==1.7.1\n# más comentarios\n".encode(
        "utf-8")
    resp = post_file(
        "requirements.txt",
        content,
        "text/plain"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
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
    resp = post_file(
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
    assert resp.status_code == 200, resp.text
    body = resp.json()
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
    resp = post_file(
        "requirements.txt",
        "uvicorn[standard]==0.30.0\n".encode("utf-8"),
        "text/plain; charset=utf-8",  # validator splits before ';'
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
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


def test_accepts_valid__with_project_name_form_field(post_file):
    """Tests that the project_name form field is accepted and used correctly."""
    resp = post_file(
        "requirements.txt",
        b"requests==2.32.3\n",
        "text/plain",
        # custom name sent as multipart form field
        form={"project_name": "MyCustomProject"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
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
    resp = post_file(
        "requirements.txt",
        # -e (editable) lines are skipped while named entries are kept
        b"-e .[all]\nfastapi>=0.110\n",
        "text/plain"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
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
    resp = post_file(
        "requirements.txt",
        # -r (include) lines are skipped while named entries are kept
        b"-r requirements-dev.txt\nrequests==2.32.3\n",
        "text/plain"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
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
    resp = post_file(
        "requirements.txt",
        # 'name @ URL' is valid PEP 508 and should pass through
        b"urllib3 @ https://github.com/urllib3/urllib3/archive/refs/tags/1.26.8.zip\n",
        "text/plain"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
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
    resp = post_file(
        "requirements.txt",
        b"anyio>=4.0.0",
        "application/json",  # wrong content type
    )
    assert resp.status_code == 415
    assert "upload a text/plain requirements.txt file" in resp.text.lower()


def test_rejects_wrong_extension_even_if_media_type_ok(post_file):
    """Tests that a wrong file extension results in a 422 error, even if the content type is correct."""
    resp = post_file(
        "not_text.bin",  # wrong extension
        b"pydantic>=2.8.0",
        "text/plain",
    )
    assert resp.status_code == 422
    assert "file must have .txt extension" in resp.text.lower()


def test_rejects_empty_file(post_file):
    """Tests that an empty requirements.txt file results in a 400 error."""
    resp = post_file("requirements.txt", b"", "text/plain")
    assert resp.status_code == 400
    assert "file is empty" in resp.text.lower()


def test_rejects_comments_only(post_file):
    """Tests that a requirements.txt file containing only comments results in a 422 error."""
    content = b"# just a comment\n   \n# another comment"
    resp = post_file("requirements.txt", content, "text/plain")
    assert resp.status_code == 422
    assert "no requirements found" in resp.text.lower()


def test_rejects_invalid_requirement_lines_single(post_file):
    """Tests that a requirements.txt file with a completely invalid line triggers a 422 error."""
    resp = post_file(
        "requirements.txt",
        b"this is not valid!!!\n",  # a completely invalid line triggers a HTTP 422
        "text/plain"
    )
    assert resp.status_code == 422
    assert "invalid requirements.txt file" in resp.text.lower()


def test_rejects_invalid_requirement_lines_mixed_list(post_file):
    """Tests that a requirements.txt file with a mix of valid and invalid lines triggers a 422 error."""
    resp = post_file(
        "requirements.txt",
        b"""
        requests==2.32.3
        invalid line !!!
        fastapi >= 0.110
        """,    # a mix of valid & invalid lines typically triggers a HTTP 422 from the parser
        "text/plain"
    )
    assert resp.status_code == 422
    assert "invalid requirements.txt file" in resp.text.lower()


def test_missing_file_param_triggers_422_from_fastapi(client):
    """Tests that missing the 'files' field in the request body triggers a 422 error."""
    # if no 'files' field is passed in, then FastAPI's validation layer should automatically throw a HTTP 422
    resp = client.post("/analyze")
    assert resp.status_code == 422


def test_non_txt_filename_but_correct_content_type(post_file):
    """Tests that a non-.txt filename with the correct content type triggers a 422 error."""
    resp = post_file(
        "image.png",    # a client could lie about the extension even if the MIME type is correct
        b"requests==2.32.3\n",
        "text/plain"
    )
    assert resp.status_code == 422
    assert "file must have .txt extension" in resp.text.lower()
