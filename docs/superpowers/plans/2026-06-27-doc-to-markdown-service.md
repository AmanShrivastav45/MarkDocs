# doc-to-markdown-service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone FastAPI microservice that converts uploaded PDF and DOCX files to Markdown with maximum content fidelity, without depending on the `markitdown` package.

**Architecture:** Two independent converter functions (`convert_pdf_to_markdown`, `convert_docx_to_markdown`) built from pure-Python libraries (`pdfplumber`/`pdfminer.six` for PDF, `mammoth`/`markdownify` for DOCX), selected by content-sniffing the uploaded bytes, wired into a single `POST /convert` FastAPI endpoint that returns a downloadable `.md` file.

**Tech Stack:** FastAPI, Uvicorn, python-multipart, pdfplumber, pdfminer.six, mammoth, markdownify, beautifulsoup4, pytest, httpx (test client transport).

## Global Constraints

- No dependency on the `markitdown` PyPI package — runtime deps are only: fastapi, uvicorn, python-multipart, pdfplumber, pdfminer.six, mammoth, markdownify, beautifulsoup4.
- No OCR, no system binaries (no Tesseract, no Poppler) — pure pip-installable Python only.
- Only `.pdf` and `.docx` are supported; file type is determined by content-sniffing, not by trusting the filename extension.
- One file per request, processed synchronously — no job queue, no batch upload.
- Python 3.10+ (matches markitdown's own floor; this plan was developed and verified against Python 3.13).
- Code ported from `microsoft/markitdown` (MIT licensed) must carry attribution; see Task 1's `NOTICE.md`.
- Every converter function must raise `app.exceptions.ConversionError` on unparseable input rather than letting a raw library exception escape — this is what the API layer maps to HTTP 422.

---

### Task 1: Project scaffolding, settings, fixtures, attribution

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/converters/__init__.py`
- Create: `app/config.py`
- Create: `NOTICE.md`
- Create: `tests/__init__.py` (empty — not strictly required by pytest, but keeps the package importable if ever needed)
- Test: `tests/test_config.py`
- Copy (already done, verify present): `tests/fixtures/test.pdf`, `tests/fixtures/test.docx`, `tests/fixtures/SPARSE-2024-INV-1234_borderless_table.pdf`, `tests/fixtures/masterformat_partial_numbering.pdf`

**Interfaces:**
- Produces: `app.config.get_settings() -> Settings` where `Settings` has fields `max_upload_size_mb: int` and `log_level: str`. Later tasks (Task 7) call `get_settings()` fresh on every request (no caching), so tests can `monkeypatch.setenv(...)` and see the change take effect immediately.

- [ ] **Step 1: Verify the fixture files already exist**

These four files were copied from `microsoft/markitdown`'s test suite (MIT licensed) during planning. Confirm they're present before continuing:

Run: `ls tests/fixtures/`
Expected output (order may vary):
```
SPARSE-2024-INV-1234_borderless_table.pdf
masterformat_partial_numbering.pdf
test.docx
test.pdf
```

If they are missing, copy them from a local checkout of `microsoft/markitdown` at `packages/markitdown/tests/test_files/{test.pdf, test.docx, SPARSE-2024-INV-1234_borderless_table.pdf, masterformat_partial_numbering.pdf}`.

- [ ] **Step 2: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
```

- [ ] **Step 3: Create `requirements.txt`**

```
fastapi>=0.138.0
uvicorn>=0.49.0
python-multipart>=0.0.20
pdfplumber>=0.11.10
pdfminer.six>=20260107
mammoth>=1.12.0
markdownify>=1.2.0
beautifulsoup4>=4.15.0
```

- [ ] **Step 4: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=9.1.0
httpx>=0.28.0
```

- [ ] **Step 5: Create the virtual environment and install dependencies**

Run:
```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install --quiet --upgrade pip
./.venv/Scripts/python.exe -m pip install --quiet -r requirements-dev.txt
```
Expected: no errors. (On macOS/Linux, use `./.venv/bin/python` instead of `./.venv/Scripts/python.exe`.)

If `.venv` already exists from earlier exploration, skip creation and just run the `pip install` line to make sure it's up to date.

- [ ] **Step 6: Create `app/__init__.py` and `app/converters/__init__.py`**

Both empty files — they just make `app` and `app.converters` importable packages.

- [ ] **Step 7: Write the failing test for settings**

Create `tests/test_config.py`:

```python
from app.config import get_settings


def test_default_settings(monkeypatch):
    monkeypatch.delenv("MAX_UPLOAD_SIZE_MB", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    settings = get_settings()
    assert settings.max_upload_size_mb == 50
    assert settings.log_level == "INFO"


def test_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "10")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    settings = get_settings()
    assert settings.max_upload_size_mb == 10
    assert settings.log_level == "DEBUG"
```

- [ ] **Step 8: Run the test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'` (or similar import error).

- [ ] **Step 9: Implement `app/config.py`**

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    max_upload_size_mb: int
    log_level: str


def get_settings() -> Settings:
    return Settings(
        max_upload_size_mb=int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
```

- [ ] **Step 10: Run the test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: 2 passed.

- [ ] **Step 11: Create `NOTICE.md`**

```markdown
# Third-Party Attribution

This project ports algorithms and test fixtures from
[microsoft/markitdown](https://github.com/microsoft/markitdown), licensed
under the MIT License. This project does **not** depend on the `markitdown`
package at runtime; the following specific pieces of code and data were
adapted from or copied out of that repository:

- `app/converters/pdf_converter.py` — the PDF form/table detection algorithm
  and MasterFormat partial-numbering merge logic are ported from
  `packages/markitdown/src/markitdown/converters/_pdf_converter.py`.
- `app/converters/markdown_utils.py` — `CustomMarkdownify` is ported from
  `packages/markitdown/src/markitdown/converters/_markdownify.py`.
- `tests/fixtures/test.pdf`, `tests/fixtures/test.docx`,
  `tests/fixtures/SPARSE-2024-INV-1234_borderless_table.pdf`,
  `tests/fixtures/masterformat_partial_numbering.pdf` — test fixtures copied
  from `packages/markitdown/tests/test_files/`.

## MIT License (microsoft/markitdown)

    MIT License

    Copyright (c) Microsoft Corporation.

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
```

- [ ] **Step 12: Create empty `tests/__init__.py`**

Empty file.

- [ ] **Step 13: Commit**

```bash
git add requirements.txt requirements-dev.txt .gitignore app/__init__.py app/converters/__init__.py app/config.py tests/__init__.py tests/test_config.py tests/fixtures NOTICE.md
git commit -m "Scaffold project, add settings module and test fixtures"
```

---

### Task 2: Content-type detector

**Files:**
- Create: `app/detectors.py`
- Test: `tests/test_detectors.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `app.detectors.detect_file_type(data: bytes) -> Optional[str]` returning `"pdf"`, `"docx"`, or `None`. Task 7 calls this to route uploads to the right converter and to reject unsupported types with a 415.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_detectors.py`:

```python
import io
import os
import zipfile

from app.detectors import detect_file_type

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as f:
        return f.read()


def test_detects_real_pdf():
    assert detect_file_type(_read("test.pdf")) == "pdf"


def test_detects_real_docx():
    assert detect_file_type(_read("test.docx")) == "docx"


def test_zip_without_word_document_xml_is_not_docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("xl/workbook.xml", "<workbook/>")
    assert detect_file_type(buf.getvalue()) is None


def test_plain_text_is_unsupported():
    assert detect_file_type(b"hello world") is None


def test_empty_bytes_is_unsupported():
    assert detect_file_type(b"") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_detectors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.detectors'`.

- [ ] **Step 3: Implement `app/detectors.py`**

```python
import io
import zipfile
from typing import Optional

PDF_MAGIC = b"%PDF"
ZIP_MAGIC = b"PK\x03\x04"


def detect_file_type(data: bytes) -> Optional[str]:
    """Sniff the actual file type from content, ignoring any claimed filename."""
    if data.startswith(PDF_MAGIC):
        return "pdf"
    if data.startswith(ZIP_MAGIC):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                if "word/document.xml" in zf.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            return None
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_detectors.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/detectors.py tests/test_detectors.py
git commit -m "Add content-sniffing file type detector for PDF/DOCX"
```

---

### Task 3: Exceptions module and CustomMarkdownify renderer

**Files:**
- Create: `app/exceptions.py`
- Create: `app/converters/markdown_utils.py`
- Test: `tests/test_markdown_utils.py`

**Interfaces:**
- Produces: `app.exceptions.ConversionError(Exception)` — raised by both converters (Tasks 4 and 6) when a document can't be parsed; caught by the API layer (Task 7) and mapped to HTTP 422.
- Produces: `app.converters.markdown_utils.CustomMarkdownify` — a `markdownify.MarkdownConverter` subclass. Used via its inherited `.convert(html: str) -> str` method. Consumed by the DOCX converter (Task 4).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_markdown_utils.py`:

```python
from app.converters.markdown_utils import CustomMarkdownify


def test_heading_converts_to_atx_style():
    html = "<h1>Title</h1><p>Body text</p>"
    md = CustomMarkdownify().convert(html)
    assert "# Title" in md


def test_javascript_link_is_stripped_to_plain_text():
    html = '<a href="javascript:alert(1)">Click</a>'
    md = CustomMarkdownify().convert(html)
    assert "javascript:" not in md
    assert "Click" in md


def test_large_data_uri_image_is_truncated():
    html = '<img src="data:image/png;base64,AAAAVERYLONGBASE64DATA==" alt="pic">'
    md = CustomMarkdownify().convert(html)
    assert "AAAAVERYLONGBASE64DATA" not in md
    assert "data:image/png;base64..." in md


def test_checkbox_input_renders_as_markdown_checkbox():
    html = '<input type="checkbox" checked>Done</input>'
    md = CustomMarkdownify().convert(html)
    assert "[x]" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_markdown_utils.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.converters.markdown_utils'`.

- [ ] **Step 3: Implement `app/exceptions.py`**

```python
class ConversionError(Exception):
    """Raised when an uploaded document cannot be parsed into Markdown."""
```

- [ ] **Step 4: Implement `app/converters/markdown_utils.py`**

Ported from `microsoft/markitdown`'s `_markdownify.py` (MIT licensed — see `NOTICE.md`), adapted to drop the markitdown-specific module path:

```python
import re
from typing import Any, Optional
from urllib.parse import quote, unquote, urlparse, urlunparse

import markdownify


class CustomMarkdownify(markdownify.MarkdownConverter):
    """
    A custom version of markdownify's MarkdownConverter. Changes include:

    - Altering the default heading style to use '#', '##', etc.
    - Removing javascript hyperlinks.
    - Truncating images with large data:uri sources.
    - Ensuring URIs are properly escaped, and do not conflict with Markdown syntax
    """

    def __init__(self, **options: Any):
        options["heading_style"] = options.get("heading_style", markdownify.ATX)
        options["keep_data_uris"] = options.get("keep_data_uris", False)
        super().__init__(**options)

    def convert_hn(
        self,
        n: int,
        el: Any,
        text: str,
        convert_as_inline: Optional[bool] = False,
        **kwargs,
    ) -> str:
        """Same as usual, but be sure to start with a new line"""
        if not convert_as_inline:
            if not re.search(r"^\n", text):
                return "\n" + super().convert_hn(n, el, text, convert_as_inline)  # type: ignore
        return super().convert_hn(n, el, text, convert_as_inline)  # type: ignore

    def convert_a(
        self,
        el: Any,
        text: str,
        convert_as_inline: Optional[bool] = False,
        **kwargs,
    ):
        """Same as usual converter, but removes Javascript links and escapes URIs."""
        prefix, suffix, text = markdownify.chomp(text)  # type: ignore
        if not text:
            return ""

        if el.find_parent("pre") is not None:
            return text

        href = el.get("href")
        title = el.get("title")

        if href:
            try:
                parsed_url = urlparse(href)  # type: ignore
                if parsed_url.scheme and parsed_url.scheme.lower() not in ["http", "https", "file"]:  # type: ignore
                    return "%s%s%s" % (prefix, text, suffix)
                href = urlunparse(parsed_url._replace(path=quote(unquote(parsed_url.path))))  # type: ignore
            except ValueError:
                return "%s%s%s" % (prefix, text, suffix)

        if (
            self.options["autolinks"]
            and text.replace(r"\_", "_") == href
            and not title
            and not self.options["default_title"]
        ):
            return "<%s>" % href
        if self.options["default_title"] and not title:
            title = href
        title_part = ' "%s"' % title.replace('"', r"\"") if title else ""
        return (
            "%s[%s](%s%s)%s" % (prefix, text, href, title_part, suffix)
            if href
            else text
        )

    def convert_img(
        self,
        el: Any,
        text: str,
        convert_as_inline: Optional[bool] = False,
        **kwargs,
    ) -> str:
        """Same as usual converter, but removes data URIs"""
        alt = el.attrs.get("alt", None) or ""
        src = el.attrs.get("src", None) or el.attrs.get("data-src", None) or ""
        title = el.attrs.get("title", None) or ""
        title_part = ' "%s"' % title.replace('"', r"\"") if title else ""
        alt = alt.replace("\n", " ")
        if (
            convert_as_inline
            and el.parent.name not in self.options["keep_inline_images_in"]
        ):
            return alt
        if src.startswith("data:") and not self.options["keep_data_uris"]:
            src = src.split(",")[0] + "..."
        return "![%s](%s%s)" % (alt, src, title_part)

    def convert_input(
        self,
        el: Any,
        text: str,
        convert_as_inline: Optional[bool] = False,
        **kwargs,
    ) -> str:
        """Convert checkboxes to Markdown [x]/[ ] syntax."""
        if el.get("type") == "checkbox":
            return "[x] " if el.has_attr("checked") else "[ ] "
        return ""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_markdown_utils.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/exceptions.py app/converters/markdown_utils.py tests/test_markdown_utils.py
git commit -m "Add ConversionError and ported CustomMarkdownify renderer"
```

---

### Task 4: DOCX converter

**Files:**
- Create: `app/converters/docx_converter.py`
- Test: `tests/test_docx_converter.py`

**Interfaces:**
- Consumes: `app.converters.markdown_utils.CustomMarkdownify` (Task 3), `app.exceptions.ConversionError` (Task 3).
- Produces: `app.converters.docx_converter.convert_docx_to_markdown(file_bytes: bytes) -> str`. Consumed by Task 7's `/convert` endpoint.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_docx_converter.py`:

```python
import os

import pytest

from app.converters.docx_converter import convert_docx_to_markdown
from app.exceptions import ConversionError

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as f:
        return f.read()


def test_docx_extracts_headings_and_body_text():
    markdown = convert_docx_to_markdown(_read("test.docx"))
    assert "# Abstract" in markdown
    assert "# Introduction" in markdown
    assert (
        "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation"
        in markdown
    )


def test_docx_truncates_embedded_image_data_uri():
    markdown = convert_docx_to_markdown(_read("test.docx"))
    assert "data:image/png;base64..." in markdown
    assert "data:image/png;base64,iVBORw0KGgoAAAANSU" not in markdown


def test_corrupt_docx_raises_conversion_error():
    with pytest.raises(ConversionError):
        convert_docx_to_markdown(b"not a real docx file")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_docx_converter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.converters.docx_converter'`.

- [ ] **Step 3: Implement `app/converters/docx_converter.py`**

```python
import io

import mammoth

from app.converters.markdown_utils import CustomMarkdownify
from app.exceptions import ConversionError


def convert_docx_to_markdown(file_bytes: bytes) -> str:
    try:
        result = mammoth.convert_to_html(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ConversionError(f"Could not parse DOCX: {exc}") from exc

    html = result.value

    try:
        markdown = CustomMarkdownify().convert(html)
    except RecursionError:
        # Very large/deeply-nested documents can exceed Python's recursion
        # limit during markdownify's recursive DOM traversal. Fall back to
        # plain text so the caller still gets usable content.
        from bs4 import BeautifulSoup

        markdown = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)

    return markdown.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_docx_converter.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/converters/docx_converter.py tests/test_docx_converter.py
git commit -m "Add DOCX to Markdown converter using mammoth + CustomMarkdownify"
```

---

### Task 5: PDF form/table detection helper

**Files:**
- Create: `app/converters/pdf_converter.py` (this task adds the detection helper only; Task 6 appends the orchestration function to the same file)
- Test: `tests/test_pdf_converter.py` (this task adds the first test class only; Task 6 appends more)

**Interfaces:**
- Produces: `app.converters.pdf_converter.PARTIAL_NUMBERING_PATTERN` (compiled regex), `app.converters.pdf_converter.extract_form_content_from_words(page: Any) -> Optional[str]`. Consumed by Task 6's orchestration function in the same module.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pdf_converter.py`:

```python
import os

import pdfplumber

from app.converters.pdf_converter import extract_form_content_from_words

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestExtractFormContentFromWords:
    def test_extracts_pipe_table_from_borderless_invoice_page(self):
        pdf_path = os.path.join(
            FIXTURES_DIR, "SPARSE-2024-INV-1234_borderless_table.pdf"
        )
        with pdfplumber.open(pdf_path) as pdf:
            content = extract_form_content_from_words(pdf.pages[0])
        assert content is not None
        assert "Product Code" in content
        assert "|" in content

    def test_returns_none_for_prose_only_page(self):
        pdf_path = os.path.join(FIXTURES_DIR, "test.pdf")
        with pdfplumber.open(pdf_path) as pdf:
            content = extract_form_content_from_words(pdf.pages[0])
        assert content is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pdf_converter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.converters.pdf_converter'`.

- [ ] **Step 3: Implement `app/converters/pdf_converter.py`**

Ported from `microsoft/markitdown`'s `_pdf_converter.py` (MIT licensed — see `NOTICE.md`). This step adds only the regex and the detection function (the orchestration function is added in Task 6, in the same file):

```python
import re
from typing import Any, Optional

# Pattern for MasterFormat-style partial numbering (e.g., ".1", ".2", ".10")
PARTIAL_NUMBERING_PATTERN = re.compile(r"^\.\d+$")


def extract_form_content_from_words(page: Any) -> Optional[str]:
    """
    Extract form-style content from a PDF page by analyzing word positions.
    This handles borderless forms/tables where words are aligned in columns.

    Returns markdown with proper table formatting:
    - Tables have pipe-separated columns with header separator rows
    - Non-table content is rendered as plain text

    Returns None if the page doesn't appear to be a form-style document,
    indicating that pdfminer should be used instead for better text spacing.
    """
    words = page.extract_words(keep_blank_chars=True, x_tolerance=3, y_tolerance=3)
    if not words:
        return None

    # Group words by their Y position (rows)
    y_tolerance = 5
    rows_by_y: dict[float, list[dict]] = {}
    for word in words:
        y_key = round(word["top"] / y_tolerance) * y_tolerance
        if y_key not in rows_by_y:
            rows_by_y[y_key] = []
        rows_by_y[y_key].append(word)

    sorted_y_keys = sorted(rows_by_y.keys())
    page_width = page.width if hasattr(page, "width") else 612

    row_info: list[dict] = []
    for y_key in sorted_y_keys:
        row_words = sorted(rows_by_y[y_key], key=lambda w: w["x0"])
        if not row_words:
            continue

        first_x0 = row_words[0]["x0"]
        last_x1 = row_words[-1]["x1"]
        line_width = last_x1 - first_x0
        combined_text = " ".join(w["text"] for w in row_words)

        x_positions = [w["x0"] for w in row_words]
        x_groups: list[float] = []
        for x in sorted(x_positions):
            if not x_groups or x - x_groups[-1] > 50:
                x_groups.append(x)

        is_paragraph = line_width > page_width * 0.55 and len(combined_text) > 60

        has_partial_numbering = False
        if row_words:
            first_word = row_words[0]["text"].strip()
            if PARTIAL_NUMBERING_PATTERN.match(first_word):
                has_partial_numbering = True

        row_info.append(
            {
                "y_key": y_key,
                "words": row_words,
                "text": combined_text,
                "x_groups": x_groups,
                "is_paragraph": is_paragraph,
                "num_columns": len(x_groups),
                "has_partial_numbering": has_partial_numbering,
            }
        )

    all_table_x_positions: list[float] = []
    for info in row_info:
        if info["num_columns"] >= 3 and not info["is_paragraph"]:
            all_table_x_positions.extend(info["x_groups"])

    if not all_table_x_positions:
        return None

    all_table_x_positions.sort()
    gaps = []
    for i in range(len(all_table_x_positions) - 1):
        gap = all_table_x_positions[i + 1] - all_table_x_positions[i]
        if gap > 5:
            gaps.append(gap)

    if gaps and len(gaps) >= 3:
        sorted_gaps = sorted(gaps)
        percentile_70_idx = int(len(sorted_gaps) * 0.70)
        adaptive_tolerance = sorted_gaps[percentile_70_idx]
        adaptive_tolerance = max(25, min(50, adaptive_tolerance))
    else:
        adaptive_tolerance = 35

    global_columns: list[float] = []
    for x in all_table_x_positions:
        if not global_columns or x - global_columns[-1] > adaptive_tolerance:
            global_columns.append(x)

    if len(global_columns) > 1:
        content_width = global_columns[-1] - global_columns[0]
        avg_col_width = content_width / len(global_columns)

        if avg_col_width < 30:
            return None

        columns_per_inch = len(global_columns) / (content_width / 72)
        if columns_per_inch > 10:
            return None

        adaptive_max_columns = int(20 * (page_width / 612))
        adaptive_max_columns = max(15, adaptive_max_columns)
        if len(global_columns) > adaptive_max_columns:
            return None
    else:
        return None

    for info in row_info:
        if info["is_paragraph"]:
            info["is_table_row"] = False
            continue
        if info["has_partial_numbering"]:
            info["is_table_row"] = False
            continue

        aligned_columns: set[int] = set()
        for word in info["words"]:
            word_x = word["x0"]
            for col_idx, col_x in enumerate(global_columns):
                if abs(word_x - col_x) < 40:
                    aligned_columns.add(col_idx)
                    break

        info["is_table_row"] = len(aligned_columns) >= 2

    table_regions: list[tuple[int, int]] = []
    i = 0
    while i < len(row_info):
        if row_info[i]["is_table_row"]:
            start_idx = i
            while i < len(row_info) and row_info[i]["is_table_row"]:
                i += 1
            end_idx = i
            table_regions.append((start_idx, end_idx))
        else:
            i += 1

    total_table_rows = sum(end - start for start, end in table_regions)
    if len(row_info) > 0 and total_table_rows / len(row_info) < 0.2:
        return None

    result_lines: list[str] = []
    num_cols = len(global_columns)

    def extract_cells(info: dict) -> list[str]:
        cells: list[str] = ["" for _ in range(num_cols)]
        for word in info["words"]:
            word_x = word["x0"]
            assigned_col = num_cols - 1
            for col_idx in range(num_cols - 1):
                col_end = global_columns[col_idx + 1]
                if word_x < col_end - 20:
                    assigned_col = col_idx
                    break
            if cells[assigned_col]:
                cells[assigned_col] += " " + word["text"]
            else:
                cells[assigned_col] = word["text"]
        return cells

    idx = 0
    while idx < len(row_info):
        info = row_info[idx]

        table_region = None
        for start, end in table_regions:
            if idx == start:
                table_region = (start, end)
                break

        if table_region:
            start, end = table_region
            table_data: list[list[str]] = []
            for table_idx in range(start, end):
                cells = extract_cells(row_info[table_idx])
                table_data.append(cells)

            if table_data:
                col_widths = [
                    max(len(row[col]) for row in table_data) for col in range(num_cols)
                ]
                col_widths = [max(w, 3) for w in col_widths]

                header = table_data[0]
                header_str = (
                    "| "
                    + " | ".join(
                        cell.ljust(col_widths[i]) for i, cell in enumerate(header)
                    )
                    + " |"
                )
                result_lines.append(header_str)

                separator = (
                    "| "
                    + " | ".join("-" * col_widths[i] for i in range(num_cols))
                    + " |"
                )
                result_lines.append(separator)

                for row in table_data[1:]:
                    row_str = (
                        "| "
                        + " | ".join(
                            cell.ljust(col_widths[i]) for i, cell in enumerate(row)
                        )
                        + " |"
                    )
                    result_lines.append(row_str)

            idx = end
        else:
            in_table = False
            for start, end in table_regions:
                if start < idx < end:
                    in_table = True
                    break

            if not in_table:
                result_lines.append(info["text"])
            idx += 1

    return "\n".join(result_lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pdf_converter.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/converters/pdf_converter.py tests/test_pdf_converter.py
git commit -m "Add PDF form/table detection helper"
```

---

### Task 6: PDF conversion orchestration

**Files:**
- Modify: `app/converters/pdf_converter.py` (append to the file created in Task 5)
- Modify: `tests/test_pdf_converter.py` (append to the file created in Task 5)

**Interfaces:**
- Consumes: `extract_form_content_from_words` and `PARTIAL_NUMBERING_PATTERN` from Task 5 (same module — no import needed, just calls the function directly), `app.exceptions.ConversionError` (Task 3).
- Produces: `app.converters.pdf_converter.merge_partial_numbering_lines(text: str) -> str`, `app.converters.pdf_converter.convert_pdf_to_markdown(file_bytes: bytes) -> str`. The latter is consumed by Task 7's `/convert` endpoint.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pdf_converter.py` (add these imports at the top alongside the existing ones, and add the new test classes at the end of the file):

```python
import re

import pytest

from app.converters.pdf_converter import convert_pdf_to_markdown
from app.exceptions import ConversionError
```

```python
class TestConvertPdfToMarkdown:
    def test_prose_pdf_has_no_tables_and_expected_content(self):
        with open(os.path.join(FIXTURES_DIR, "test.pdf"), "rb") as f:
            markdown = convert_pdf_to_markdown(f.read())
        assert "|" not in markdown
        assert "Introduction" in markdown
        assert "agents" in markdown
        assert "multi-agent" in markdown
        assert len(markdown) > 1000

    def test_borderless_table_pdf_extracts_pipe_table(self):
        with open(
            os.path.join(FIXTURES_DIR, "SPARSE-2024-INV-1234_borderless_table.pdf"),
            "rb",
        ) as f:
            markdown = convert_pdf_to_markdown(f.read())
        assert "Product Code" in markdown
        assert "SKU-8847" in markdown
        assert markdown.count("|") > 50

    def test_masterformat_partial_numbering_is_merged_with_following_text(self):
        with open(
            os.path.join(FIXTURES_DIR, "masterformat_partial_numbering.pdf"), "rb"
        ) as f:
            markdown = convert_pdf_to_markdown(f.read())
        assert re.search(r"\.1\s+The intent", markdown)
        isolated = [
            line.strip()
            for line in markdown.split("\n")
            if re.match(r"^\.\d+$", line.strip())
        ]
        assert isolated == []

    def test_corrupt_pdf_raises_conversion_error(self):
        with pytest.raises(ConversionError):
            convert_pdf_to_markdown(b"%PDF-not-real-content")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pdf_converter.py -v`
Expected: FAIL — `ImportError: cannot import name 'convert_pdf_to_markdown'` for the new test class (the Task 5 tests should still pass).

- [ ] **Step 3: Append the orchestration logic to `app/converters/pdf_converter.py`**

Add these imports at the top of the file (alongside the existing `import re` and `from typing import Any, Optional`):

```python
import io

import pdfminer.high_level
import pdfplumber

from app.exceptions import ConversionError
```

Append this function and the merge helper to the end of the file:

```python
def merge_partial_numbering_lines(text: str) -> str:
    """
    Post-process extracted text to merge MasterFormat-style partial numbering
    with the following text line.

    MasterFormat documents use partial numbering like:
        .1  The intent of this Request for Proposal...
        .2  Available information relative to...

    Some PDF extractors split these into separate lines:
        .1
        The intent of this Request for Proposal...

    This function merges them back together.
    """
    lines = text.split("\n")
    result_lines: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if PARTIAL_NUMBERING_PATTERN.match(stripped):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines):
                next_line = lines[j].strip()
                result_lines.append(f"{stripped} {next_line}")
                i = j + 1
            else:
                result_lines.append(line)
                i += 1
        else:
            result_lines.append(line)
            i += 1

    return "\n".join(result_lines)


def convert_pdf_to_markdown(file_bytes: bytes) -> str:
    """
    Converts PDF bytes to Markdown.
    Supports extracting tables into aligned Markdown format (via pdfplumber).
    Falls back to pdfminer if pdfplumber is missing content or fails.
    """
    pdf_bytes = io.BytesIO(file_bytes)

    try:
        markdown_chunks: list[str] = []
        form_page_count = 0

        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages:
                page_content = extract_form_content_from_words(page)

                if page_content is not None:
                    form_page_count += 1
                    if page_content.strip():
                        markdown_chunks.append(page_content)
                else:
                    text = page.extract_text()
                    if text and text.strip():
                        markdown_chunks.append(text.strip())

                page.close()

        if form_page_count == 0:
            pdf_bytes.seek(0)
            markdown = pdfminer.high_level.extract_text(pdf_bytes)
        else:
            markdown = "\n\n".join(markdown_chunks).strip()
    except Exception:
        pdf_bytes.seek(0)
        try:
            markdown = pdfminer.high_level.extract_text(pdf_bytes)
        except Exception as exc:
            raise ConversionError(f"Could not parse PDF: {exc}") from exc

    if not markdown:
        pdf_bytes.seek(0)
        try:
            markdown = pdfminer.high_level.extract_text(pdf_bytes)
        except Exception:
            pass

    return merge_partial_numbering_lines(markdown).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pdf_converter.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/converters/pdf_converter.py tests/test_pdf_converter.py
git commit -m "Add PDF conversion orchestration with pdfminer fallback"
```

---

### Task 7: FastAPI application — `/health` and `/convert`

**Files:**
- Create: `app/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `app.config.get_settings` (Task 1), `app.detectors.detect_file_type` (Task 2), `app.exceptions.ConversionError` (Task 3), `app.converters.docx_converter.convert_docx_to_markdown` (Task 4), `app.converters.pdf_converter.convert_pdf_to_markdown` (Task 6).
- Produces: `app.main.app` — the FastAPI application instance, run via `uvicorn app.main:app`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api.py`:

```python
import io
import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_convert_pdf_returns_markdown_file():
    with open(os.path.join(FIXTURES_DIR, "test.pdf"), "rb") as f:
        response = client.post(
            "/convert", files={"file": ("test.pdf", f, "application/pdf")}
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment" in response.headers["content-disposition"]
    assert "Introduction" in response.text


def test_convert_docx_returns_markdown_file():
    with open(os.path.join(FIXTURES_DIR, "test.docx"), "rb") as f:
        response = client.post(
            "/convert",
            files={
                "file": (
                    "test.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert response.status_code == 200
    assert "# Abstract" in response.text


def test_convert_rejects_unsupported_file_type():
    response = client.post(
        "/convert",
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 415


def test_convert_returns_422_for_corrupt_pdf():
    response = client.post(
        "/convert",
        files={
            "file": (
                "broken.pdf",
                io.BytesIO(b"%PDF-not-real-content"),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 422


def test_convert_rejects_oversized_file(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "0")
    big_content = b"%PDF-1.4" + b"0" * 1024
    response = client.post(
        "/convert",
        files={"file": ("big.pdf", io.BytesIO(big_content), "application/pdf")},
    )
    assert response.status_code == 413
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Implement `app/main.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_api.py -v`
Expected: 6 passed.

- [ ] **Step 5: Run the full test suite**

Run: `./.venv/Scripts/python.exe -m pytest -v`
Expected: all tests across every module pass (config, detectors, markdown_utils, docx_converter, pdf_converter, api).

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_api.py
git commit -m "Add FastAPI app with /health and /convert endpoints"
```

---

### Task 8: Dockerfile, README, and manual smoke test

**Files:**
- Create: `Dockerfile`
- Create: `README.md`

**Interfaces:**
- Consumes: `app.main.app` (Task 7) as the Uvicorn entry point.
- Produces: nothing consumed by other tasks — this is the final, user-facing task.

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `README.md`**

```markdown
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
```

- [ ] **Step 3: Manual smoke test — run the server and hit it for real**

Run (in the background or a separate terminal):
```bash
./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 &
```

Then:
```bash
curl -s http://127.0.0.1:8000/health
curl -s -F "file=@tests/fixtures/test.pdf" http://127.0.0.1:8000/convert -o /tmp/out.md -D -
head -c 300 /tmp/out.md
```

Expected: `/health` returns `{"status":"ok"}`; the `/convert` call returns HTTP 200 with `Content-Disposition: attachment; filename="test.md"`, and `/tmp/out.md` starts with the academic paper's title/author text.

Stop the server afterward.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile README.md
git commit -m "Add Dockerfile and README"
```

---

## Self-Review Notes

- **Spec coverage:** architecture/deps (Task 1), API contract incl. content-sniffing and size limits (Tasks 2, 7), PDF pipeline incl. table detection and partial-numbering merge (Tasks 5–6), DOCX pipeline incl. CustomMarkdownify (Tasks 3–4), error handling table fully covered by Task 7's status codes (415/413/422/500) and the empty-output warning header, testing strategy (unit tests per task + integration tests in Task 7), packaging (Task 8 Dockerfile/README). NOTICE.md added in Task 1 to satisfy MIT attribution for ported code and fixtures, which the spec implied but didn't spell out as a file — added during planning.
- **Type consistency:** `convert_pdf_to_markdown(file_bytes: bytes) -> str` and `convert_docx_to_markdown(file_bytes: bytes) -> str` have matching signatures, both raising `ConversionError`, both consumed identically in Task 7. `detect_file_type(data: bytes) -> Optional[str]` returns exactly `"pdf"`/`"docx"`/`None`, matching the `if file_type == "pdf"` branch in Task 7.
- **No placeholders:** every step above contains complete, empirically-verified code — all converter logic, detector logic, and the FastAPI app were run against the real copied fixtures (`test.pdf`, `test.docx`, the borderless-table PDF, and the MasterFormat PDF) during planning, including the corrupt-file and oversized-file error paths, before being written into this plan.
