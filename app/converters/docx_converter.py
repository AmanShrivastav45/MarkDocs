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
