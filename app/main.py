import re

from fastapi import FastAPI, File, HTTPException, Response, UploadFile

from app.config import get_settings
from app.converters.docx_converter import convert_docx_to_markdown
from app.converters.pdf_converter import convert_pdf_to_markdown
from app.detectors import detect_file_type
from app.exceptions import ConversionError

app = FastAPI(title="doc-to-markdown-service")

EMPTY_OUTPUT_THRESHOLD = 20
CHUNK_SIZE = 1024 * 1024  # 1 MB


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


async def _read_within_limit(file: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in chunks, aborting as soon as it exceeds max_bytes
    instead of buffering an oversized file fully into memory first."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@app.post("/convert")
async def convert(file: UploadFile = File(...)) -> Response:
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    data = await _read_within_limit(file, max_bytes)

    file_type = detect_file_type(data)
    if file_type is None:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type: only PDF and DOCX are supported",
        )

    try:
        if file_type == "pdf":
            markdown = convert_pdf_to_markdown(data)
        else:
            markdown = convert_docx_to_markdown(data)
    except ConversionError as exc:
        raise HTTPException(
            status_code=422, detail=f"Could not parse document: {exc}"
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal conversion error")

    stem = (file.filename or "document").rsplit(".", 1)[0]
    stem = re.sub(r'[\r\n"]', "", stem) or "document"

    headers = {"Content-Disposition": f'attachment; filename="{stem}.md"'}
    if len(markdown.strip()) < EMPTY_OUTPUT_THRESHOLD:
        headers["X-Conversion-Warning"] = "empty-or-near-empty-output"

    return Response(content=markdown, media_type="text/markdown", headers=headers)
