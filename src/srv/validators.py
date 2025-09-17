import requirements
from typing import List
from fastapi import HTTPException, UploadFile, status

# only .txt files are allowed to be uploaded
ALLOWED_CONTENT_TYPES = ("text/plain",)


async def validate_requirements_file(file: UploadFile) -> bool:
    # check if the file has the correct MIME type
    # the content type might have a ";" in it (source: https://greenbytes.de/tech/webdav/rfc2616.html#rfc.section.14.17), so we're accounting for that
    ct: str = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a text/plain requirements.txt file."
        )
    if not (file.filename and file.filename.lower().endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must have .txt extension."
        )
    
    # decode the raw text file (throws an error if the file can't be decoded)
    raw_text: bytes = await file.read()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty."
        )
    try:
        text = raw_text.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text file is malformed and cannot be decoded."
        )
    
    # skip all directive-like lines that start with '-' (includes -r, -c, -f, etc.)
    # NOTE: we do this because some files that have these *are* valid, but requirements-parser thinks 
    # they're not. we also do this in the parsing function, but it doesn't need an explanation there!
    text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("-"))

    # use requirements-parser to ensure the requirements can be parsed from the file
    try:
        parsed_reqs = list(requirements.parse(text))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid requirements.txt file."
        )
    
    if not parsed_reqs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No requirements found."
        )
    
    return True



async def parse_requirements_file(file: UploadFile) -> List[str]:
    # decode the raw text file
    raw_text: bytes = await file.read()
    text = raw_text.decode("utf-8")
    
    # skip all directive-like lines that start with '-' (includes -r, -c, -f, etc.)
    text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("-"))

    # next, use requirements-parser to get all of the requirements
    try:
        parsed_reqs = list(requirements.parse(text))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid requirements.txt file."
        )

    # keep any requirements with a .name field
    reqs: list[str] = []
    for req in parsed_reqs:
        if getattr(req, "name"):
            reqs.append(getattr(req, "line", str(req)).strip())

    # ignore all blank lines & comments
    reqs = [ln for ln in (ln.strip() for ln in reqs)
            if ln and not ln.lstrip().startswith("#")]
    if not reqs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No requirements found."
        )

    return reqs
