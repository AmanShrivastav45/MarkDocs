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
