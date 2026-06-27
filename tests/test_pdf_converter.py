import os
import re

import pdfplumber
import pytest

from app.converters.pdf_converter import convert_pdf_to_markdown, extract_form_content_from_words
from app.exceptions import ConversionError

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
