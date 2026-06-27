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
