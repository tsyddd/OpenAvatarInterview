from handlers.interview.services.report_html_renderer import ReportHtmlRenderer


def test_html_renderer_outputs_full_html_document():
    renderer = ReportHtmlRenderer()
    html = renderer.render("# 标题\n\n- **姓名**：张三")

    assert "<html" in html
    assert "report-root" in html
    assert "<strong>姓名</strong>" in html


def test_html_renderer_supports_markdown_tables():
    renderer = ReportHtmlRenderer()
    markdown = """
| 列1 | 列2 |
| --- | --- |
| A | B |
""".strip()

    html = renderer.render(markdown)

    assert "<table" in html
    assert "<th>列1</th>" in html
    assert "<td>A</td>" in html
