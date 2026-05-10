"""Tests for src.gui.markdown_renderer."""

import pytest

from src.gui.markdown_renderer import (
    _convert_markdown_inline,
    _convert_markdown_links,
    create_anchor_id,
    markdown_to_html,
)

pytestmark = pytest.mark.unit


class TestCreateAnchorId:
    def test_spaces_become_hyphens(self):
        assert create_anchor_id("Hello World") == "hello-world"

    def test_dots_removed(self):
        assert create_anchor_id("v1.0.2") == "v102"

    def test_ampersand_becomes_and(self):
        assert create_anchor_id("Terms & Conditions") == "terms-and-conditions"


class TestConvertMarkdownLinks:
    def test_basic_link(self):
        result = _convert_markdown_links("[GitHub](https://github.com)")
        assert result == '<a href="https://github.com">GitHub</a>'

    def test_no_link_unchanged(self):
        assert _convert_markdown_links("plain text") == "plain text"


class TestConvertMarkdownInline:
    def test_bold_double_star(self):
        assert "<strong>bold</strong>" in _convert_markdown_inline("**bold**")

    def test_bold_double_underscore(self):
        assert "<strong>bold</strong>" in _convert_markdown_inline("__bold__")

    def test_italic_single_star(self):
        assert "<em>italic</em>" in _convert_markdown_inline("*italic*")

    def test_inline_code(self):
        result = _convert_markdown_inline("`code`")
        assert "<code>code</code>" in result

    def test_code_protects_star_content(self):
        # Stars inside backticks should not become italic/bold
        result = _convert_markdown_inline("`vehicle_Name*`")
        assert "<em>" not in result
        assert "vehicle_Name*" in result

    def test_code_escapes_html(self):
        # Angle brackets inside a code span should render as literal text
        result = _convert_markdown_inline("`<img>`")
        assert "&lt;img&gt;" in result

    def test_bold_runs_before_italic(self):
        # **x** should not be parsed as two *italic* runs
        result = _convert_markdown_inline("**bold**")
        assert "<strong>bold</strong>" in result
        assert "<em>" not in result


class TestMarkdownToHtml:
    def test_returns_html_document(self):
        html = markdown_to_html("# Title\n\nParagraph.")
        assert html.startswith("<html>")
        assert "<h1" in html
        assert "<p>" in html

    def test_h1_gets_anchor(self):
        html = markdown_to_html("# My Section")
        assert "id='my-section'" in html

    def test_h2_h3_get_anchors(self):
        html = markdown_to_html("## Two\n### Three")
        assert "id='two'" in html
        assert "id='three'" in html

    def test_unordered_list(self):
        html = markdown_to_html("- item one\n- item two")
        assert "<ul>" in html
        assert "<li>item one</li>" in html

    def test_ordered_list(self):
        html = markdown_to_html("1. first\n2. second")
        assert "<ol>" in html
        assert "<li>first</li>" in html

    def test_code_block(self):
        html = markdown_to_html("```\ncode here\n```")
        assert "<pre><code>" in html
        assert "code here" in html
        assert "</pre>" in html

    def test_colors_injected(self):
        html = markdown_to_html(
            "text",
            text_color="#ff0000",
            base_color="#00ff00",
            link_color="#0000ff",
        )
        assert "#ff0000" in html
        assert "#00ff00" in html
        assert "#0000ff" in html

    def test_empty_input(self):
        html = markdown_to_html("")
        assert "<html>" in html
        assert "</html>" in html

    def test_unclosed_list_closed_at_end(self):
        html = markdown_to_html("- only item")
        assert "</ul>" in html

    def test_unclosed_code_block_closed_at_end(self):
        html = markdown_to_html("```\nunterminated")
        assert "</pre>" in html
