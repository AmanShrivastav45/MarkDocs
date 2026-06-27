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
