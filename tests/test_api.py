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
