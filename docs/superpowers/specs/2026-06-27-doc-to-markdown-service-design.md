# doc-to-markdown-service — Design Spec

Date: 2026-06-27

## Purpose

A standalone FastAPI microservice that converts uploaded PDF and DOCX documents
into Markdown, for use by the NORMA project. It is inspired by and modeled on
[microsoft/markitdown](https://github.com/microsoft/markitdown)'s PDF and DOCX
conversion strategy, but does **not** depend on the `markitdown` package
itself — `pip install markitdown` is not reliably available in the target
company infrastructure. Instead, this service depends only on the underlying
pure-Python libraries markitdown itself uses for these two formats, and ports
(with attribution) the specific extraction algorithms that make markitdown's
output accurate.

Primary goal: **maximize content fidelity** (text, structure, and tables) when
converting PDF/DOCX to Markdown, using only pip-installable, pure-Python
dependencies — no system binaries (e.g. no Tesseract/Poppler), no OCR, no
compiled native extensions required.

## Non-goals (v1)

- OCR / scanned image PDFs are explicitly out of scope. Documents are assumed
  to have a real text layer or real DOCX XML content.
- No support for formats other than `.pdf` and `.docx` (no pptx, xlsx, images,
  etc.)
- No async job queue / background processing — conversions are synchronous
  within the request lifecycle.
- No batch upload (one file per request).
- Not embedded into NORMA's existing FastAPI process — this is a separate
  deployable service NORMA calls over HTTP.

## Architecture & dependency stack

Pure-Python dependencies only, mirroring markitdown's own per-format choices:

| Format | Libraries | Role |
|---|---|---|
| PDF | `pdfplumber`, `pdfminer.six` | `pdfplumber` for layout-aware extraction plus table/form detection; `pdfminer.six` as a fallback for plain prose pages and whole-document fallback |
| DOCX | `mammoth`, `markdownify`, `beautifulsoup4` | `mammoth` converts DOCX→HTML preserving headings/lists/tables/styles/links/images; `markdownify` converts that HTML→Markdown |
| Core | `fastapi`, `uvicorn`, `python-multipart` | web service, ASGI server, multipart form parsing |

`python-docx` was considered and rejected for DOCX conversion: it only
exposes low-level paragraph/run/table objects with no awareness of heading
styles or nested-list structure, so reaching markitdown-level fidelity with it
would require reimplementing most of what `mammoth` already does. `mammoth`
is pure-Python, MIT licensed, has no compiled extensions, and is a widely used
package — same trade-off markitdown itself made.

markitdown's PDF table/form-detection logic (in
`packages/markitdown/src/markitdown/converters/_pdf_converter.py`) and its
custom Markdown renderer (`_markdownify.py`'s `_CustomMarkdownify`) are
MIT-licensed. This project ports those algorithms into its own converter
modules, with an attribution comment crediting the original source and
license, rather than taking a runtime dependency on the `markitdown` package.

## API contract

- `POST /convert`
  - Accepts `multipart/form-data` with a single file field named `file`.
  - Accepted types: `.pdf`, `.docx` (validated by content sniffing, not just
    extension — see Validation below).
  - On success: returns the converted Markdown as a downloadable file.
    - `Content-Type: text/markdown`
    - `Content-Disposition: attachment; filename="<original_stem>.md"`
  - On failure: returns a JSON error body (see Error handling below).
- `GET /health`
  - Returns `{"status": "ok"}`. No auth, used for liveness/readiness checks.

### Validation

- **Content sniffing**: the file's actual bytes are inspected regardless of
  the claimed filename/extension:
  - PDF: starts with `%PDF` magic bytes.
  - DOCX: is a valid ZIP archive (`PK\x03\x04` signature) containing a
    `word/document.xml` entry (distinguishes DOCX from other OOXML formats
    like `.xlsx`/`.pptx`, which are also ZIPs).
  - Anything else → 415.
- **Max upload size**: configurable via `MAX_UPLOAD_SIZE_MB` env var, default
  `50`. Enforced by checking `Content-Length` and by streaming/aborting if the
  actual body exceeds the limit. Exceeding it → 413.

## Conversion pipeline

### PDF (`app/converters/pdf_converter.py`)

Ported from markitdown's `_pdf_converter.py` logic:

1. Open the PDF with `pdfplumber`.
2. For each page:
   - Attempt form/table-aware extraction: cluster extracted words by Y
     position into rows, detect aligned X-position column groups across the
     page, and classify the page as table-like if enough rows align into 2+
     consistent columns. Render detected tables as proper Markdown pipe
     tables; render non-table rows on the page as plain text lines.
   - If the page is not table-like, fall back to `page.extract_text()` for
     that page (plain prose).
3. If **no** page in the whole document was classified as table-like, discard
   the pdfplumber output and instead run `pdfminer.six`'s
   `extract_text()` over the whole document (better whitespace/line-break
   handling for pure prose documents).
4. If pdfplumber raises an exception at any point, or the final markdown is
   empty, fall back to `pdfminer.six`'s `extract_text()` for the whole
   document.
5. Post-process: merge MasterFormat-style partial numbering lines (e.g. a
   line containing only `.1` followed by a separate text line) back into a
   single line, matching markitdown's behavior, since some PDF extractors
   split these unnecessarily.

### DOCX (`app/converters/docx_converter.py`)

1. `mammoth.convert_to_html(file_stream)` → semantic HTML (headings as
   `<h1>`-`<h6>`, lists, tables, bold/italic, hyperlinks, images as `<img>`).
2. Feed the HTML into a custom `markdownify.MarkdownConverter` subclass
   (`app/converters/markdown_utils.py`, ported from markitdown's
   `_CustomMarkdownify`):
   - ATX-style `#` headings (never the `===`/`---` underline style).
   - Hyperlinks: strips `javascript:` links, percent-escapes URI paths so
     they don't collide with Markdown syntax.
   - Images: alt-text only; `data:` URIs are truncated rather than inlined in
     full, to keep output lightweight.
   - Checkbox `<input>` elements render as `[x]`/`[ ]`.
3. No title/frontmatter block — the first Markdown heading in the body serves
   as the document's effective title. No YAML frontmatter is generated.

## Error handling

All error responses are JSON via FastAPI `HTTPException`; only the success
path returns a raw file body.

| Condition | Status | Body |
|---|---|---|
| Unsupported/unrecognized file type | 415 | `{"detail": "Unsupported file type: ..."}` |
| File exceeds max size | 413 | `{"detail": "File exceeds maximum size of N MB"}` |
| Corrupt/unparseable file (e.g. password-protected PDF, malformed DOCX) | 422 | `{"detail": "Could not parse document: <reason>"}` |
| Conversion succeeded but produced empty/near-empty output (stripped output is empty or under 20 characters) | 200 | Markdown file returned as-is, with an added `X-Conversion-Warning: empty-or-near-empty-output` response header |
| Unexpected internal error | 500 | `{"detail": "Internal conversion error"}`; full exception logged server-side (not leaked to the client) |

## Testing strategy

- **Unit tests** (`tests/test_pdf_converter.py`, `tests/test_docx_converter.py`):
  call converter functions directly against fixture files covering:
  - Plain prose only.
  - A table/form-style page (PDF) / a table (DOCX).
  - Headings and nested lists.
  - A deliberately corrupt/truncated file (expect a clear raised exception,
    not a crash).
- **Integration tests** (`tests/test_api.py`): use FastAPI's `TestClient`
  against `/convert` and `/health`, asserting status codes, response headers
  (`Content-Disposition`, `Content-Type`), and that returned Markdown
  contains expected structural markers (e.g. `#` headings, `|` table rows).
- Fixture files live under `tests/fixtures/`.

## Packaging & deployment

- `requirements.txt` pins: `fastapi`, `uvicorn`, `python-multipart`,
  `pdfplumber`, `pdfminer.six`, `mammoth`, `markdownify`, `beautifulsoup4`.
  Explicitly **not** `markitdown`.
- `Dockerfile`: simple `python:3.x-slim` base, `pip install -r
  requirements.txt`, run via `uvicorn app.main:app`. No system packages
  required beyond the Python base image.
- Configuration via environment variables (`MAX_UPLOAD_SIZE_MB`, `LOG_LEVEL`),
  read through `app/config.py` with sane defaults — no required config to run
  locally.
- `README.md` documents how to run locally, the `/convert` contract, and the
  explicit non-goals (no OCR, no batch, sync-only) so future maintainers don't
  assume those exist.

## Project layout

```
app/
  main.py              # FastAPI app, /convert, /health
  config.py            # env-based settings
  detectors.py         # content-sniffing for pdf/docx
  exceptions.py        # conversion-specific exception types
  converters/
    pdf_converter.py
    docx_converter.py
    markdown_utils.py  # CustomMarkdownify subclass
tests/
  fixtures/
  test_pdf_converter.py
  test_docx_converter.py
  test_api.py
requirements.txt
Dockerfile
README.md
```
