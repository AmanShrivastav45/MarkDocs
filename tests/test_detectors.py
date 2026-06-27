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
