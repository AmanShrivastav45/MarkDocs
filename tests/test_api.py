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


def test_convert_sets_warning_header_for_empty_output():
    blank_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n209\n%%EOF\n"
    )
    response = client.post(
        "/convert",
        files={"file": ("blank.pdf", io.BytesIO(blank_pdf), "application/pdf")},
    )
    assert response.status_code == 200
    assert response.headers["x-conversion-warning"] == "empty-or-near-empty-output"
