from handlers.interview.services.report_pdf_renderer import ReportPdfRenderer


def test_normalize_markdown_strips_fenced_wrapper_and_bold_markers():
    renderer = ReportPdfRenderer()
    markdown = """```markdown
# 标题

- **姓名**：张三
```"""

    normalized = renderer._normalize_markdown(markdown)

    assert "```" not in normalized
    assert "**" not in normalized
    assert "姓名：张三" in normalized


def test_parse_blocks_extracts_markdown_table():
    renderer = ReportPdfRenderer()
    markdown = """
| 列1 | 列2 |
|-----|-----|
| A   | B   |
| C   | D   |
""".strip()

    blocks = renderer._parse_blocks(renderer._normalize_markdown(markdown))

    assert len(blocks) == 1
    assert blocks[0]["type"] == "table"
    assert blocks[0]["rows"][0] == ["列1", "列2"]
    assert blocks[0]["rows"][1] == ["A", "B"]
    assert blocks[0]["rows"][2] == ["C", "D"]
