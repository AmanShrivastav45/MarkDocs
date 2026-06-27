# doc-to-markdown-service

A standalone FastAPI microservice that converts PDF and DOCX documents to
Markdown, without depending on the `markitdown` PyPI package. See
`NOTICE.md` for attribution of ported algorithms and test fixtures.

## Why no `markitdown` dependency

This service reimplements the specific PDF and DOCX extraction strategies
that make `markitdown` accurate, using only pure-Python, pip-installable
libraries: `pdfplumber`/`pdfminer.six` for PDF, `mammoth`/`markdownify` for
DOCX. No system binaries (no Tesseract, no Poppler) are required.

## Non-goals

- No OCR / scanned PDF support.
- No formats other than `.pdf` and `.docx`.
- No background job queue — conversion happens synchronously per request.
- No batch upload — one file per request.

## Running locally

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

## API

### `POST /convert`

`multipart/form-data` with a single `file` field (`.pdf` or `.docx`).

- `200`: returns the converted Markdown as a downloadable `.md` file. If the
  extracted content is empty or near-empty (e.g. a scanned PDF with no text
  layer), the response still returns `200` but includes an
  `X-Conversion-Warning: empty-or-near-empty-output` header.
- `415`: unsupported file type (checked by content-sniffing, not extension).
- `413`: file exceeds `MAX_UPLOAD_SIZE_MB` (default 50).
- `422`: file claims to be a PDF/DOCX but could not be parsed.
- `500`: unexpected internal error.

### `GET /health`

Returns `{"status": "ok"}`.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum accepted upload size |
| `LOG_LEVEL` | `INFO` | Reserved for future logging configuration |

## Testing

```bash
./.venv/Scripts/python.exe -m pytest -v
```
