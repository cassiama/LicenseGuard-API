import io
import pytest
from starlette.datastructures import Headers
from fastapi import HTTPException
from fastapi.datastructures import UploadFile
from srv.validators import validate_requirements_file, parse_requirements_file


def _uf(filename: str, data: bytes, content_type: str) -> UploadFile:
    # FastAPI's UploadFile is a child of Starlette's UploadFile, so we can directly pass in these fields w/o errors
    return UploadFile(
        filename=filename,
        file=io.BytesIO(data),
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
async def test_validator_ok_roundtrip():
    uf = _uf("requirements.txt", b"requests==2.32.3\n", "text/plain")
    result = await validate_requirements_file(uf)
    assert result == True


@pytest.mark.asyncio
async def test_parser_ok_roundtrip():
    uf = _uf("requirements.txt", b"requests==2.32.3\n", "text/plain")
    lines = await parse_requirements_file(uf)
    assert lines == ["requests==2.32.3"]


@pytest.mark.asyncio
async def test_validator_accepts_pep508_direct_url():
    uf = _uf(
        "requirements.txt",
        b"urllib3 @ https://github.com/urllib3/urllib3/archive/refs/tags/1.26.8.zip\n",
        "text/plain",
    )
    result = await validate_requirements_file(uf)
    assert result == True


@pytest.mark.asyncio
async def test_parser_accepts_pep508_direct_url():
    uf = _uf(
        "requirements.txt",
        b"urllib3 @ https://github.com/urllib3/urllib3/archive/refs/tags/1.26.8.zip\n",
        "text/plain",
    )
    lines = await parse_requirements_file(uf)
    assert any("urllib3 @" in ln for ln in lines)


@pytest.mark.asyncio
async def test_validator_accepts_editable_and_keeps_named():
    uf = _uf("requirements.txt", b"-e .[all]\nfastapi>=0.110\n", "text/plain")
    result = await validate_requirements_file(uf)
    assert result == True


@pytest.mark.asyncio
async def test_parser_accepts_editable_and_keeps_named():
    uf = _uf("requirements.txt", b"-e .[all]\nfastapi>=0.110\n", "text/plain")
    lines = await parse_requirements_file(uf)
    # editable line is skipped by the parser
    assert not any(line.startswith("-e ") for line in lines)
    # named requirement is still present
    assert "fastapi>=0.110" in lines


@pytest.mark.asyncio
async def test_validator_accepts_includes():
    uf = _uf("requirements.txt",
             b"-r other.txt\nrequests==2.32.3\n", "text/plain")
    result = await validate_requirements_file(uf)
    assert result == True


@pytest.mark.asyncio
async def test_parser_accepts_includes():
    uf = _uf("requirements.txt",
             b"-r other.txt\nrequests==2.32.3\n", "text/plain")
    lines = await parse_requirements_file(uf)
    # includes line is skipped by the parser
    assert not any(line.startswith("-r ") for line in lines)
    # named requirement is still present
    assert lines == ["requests==2.32.3"]


@pytest.mark.asyncio
async def test_validator_wrong_media_type():
    uf = _uf("requirements.txt", b"requests==2.32.3\n",
             "application/octet-stream")
    with pytest.raises(HTTPException) as ex:
        await validate_requirements_file(uf)
    assert ex.value.status_code == 415
    assert "upload a text/plain requirements.txt file" in str(
        ex.value.detail).lower()


@pytest.mark.asyncio
async def test_validator_wrong_extension():
    uf = _uf("not_a_text.bin", b"anyio>=4\n", "text/plain")
    with pytest.raises(HTTPException) as ex:
        await validate_requirements_file(uf)
    assert ex.value.status_code == 422
    assert "must have .txt extension" in str(ex.value.detail).lower()


@pytest.mark.asyncio
async def test_validator_empty_file():
    uf = _uf("requirements.txt", b"", "text/plain")
    with pytest.raises(HTTPException) as ex:
        await validate_requirements_file(uf)
    assert ex.value.status_code == 400
    assert "file is empty" in str(ex.value.detail).lower()


@pytest.mark.asyncio
async def test_parser_empty_file():
    uf = _uf("requirements.txt", b"", "text/plain")
    with pytest.raises(HTTPException) as ex:
        await parse_requirements_file(uf)
    assert ex.value.status_code == 400
    assert "file is empty" in str(ex.value.detail).lower()


@pytest.mark.asyncio
async def test_validator_invalid_utf8_returns_422():
    uf = _uf("requirements.txt", b"\xff\xfe\xfa", "text/plain")
    with pytest.raises(HTTPException) as ex:
        await validate_requirements_file(uf)
    assert ex.value.status_code == 422
    assert "cannot be decoded" in str(ex.value.detail).lower()


@pytest.mark.asyncio
async def test_parser_invalid_utf8_returns_422():
    uf = _uf("requirements.txt", b"\xff\xfe\xfa", "text/plain")
    with pytest.raises(HTTPException) as ex:
        await parse_requirements_file(uf)
    assert ex.value.status_code == 422
    assert "cannot be decoded" in str(ex.value.detail).lower()


@pytest.mark.asyncio
async def test_validator_all_invalid_lines_raise_generic_422():
    uf = _uf("requirements.txt", b"this is not valid!!!\n", "text/plain")
    with pytest.raises(HTTPException) as ex:
        await validate_requirements_file(uf)
    assert ex.value.status_code == 422
    assert "invalid requirements.txt file" in str(ex.value.detail).lower()


@pytest.mark.asyncio
async def test_parser_all_invalid_lines_raise_generic_422():
    uf = _uf("requirements.txt", b"this is not valid!!!\n", "text/plain")
    with pytest.raises(HTTPException) as ex:
        await parse_requirements_file(uf)
    assert ex.value.status_code == 422
    assert "invalid requirements.txt file" in str(ex.value.detail).lower()


@pytest.mark.asyncio
async def test_validator_mixed_valid_and_invalid_lines_raises_422():
    data = b"requests==2.32.3\ninvalid line !!!\nfastapi >= 0.110\n"
    uf = _uf("requirements.txt", data, "text/plain")
    with pytest.raises(HTTPException) as ex:
        await validate_requirements_file(uf)
    assert ex.value.status_code == 422
    assert "invalid requirements.txt file" in str(ex.value.detail).lower()


@pytest.mark.asyncio
async def test_parser_mixed_valid_and_invalid_lines_raises_422():
    data = b"requests==2.32.3\ninvalid line !!!\nfastapi >= 0.110\n"
    uf = _uf("requirements.txt", data, "text/plain")
    with pytest.raises(HTTPException) as ex:
        await parse_requirements_file(uf)
    assert ex.value.status_code == 422
    assert "invalid requirements.txt file" in str(ex.value.detail).lower()
