from __future__ import annotations

import re

from markdown_it import MarkdownIt


class ReportHtmlRenderer:
    def __init__(self) -> None:
        self._md = MarkdownIt("commonmark", {"html": False, "breaks": True}).enable("table")

    def render(self, markdown: str) -> str:
        normalized = self._normalize_markdown(markdown or "面试报告暂无内容。")
        body = self._md.render(normalized)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>面试报告</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f8fafc;
        --card: #ffffff;
        --text: #1e293b;
        --muted: #64748b;
        --line: #e2e8f0;
        --accent: #2563eb;
        --accent-soft: #eff6ff;
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        padding: 32px;
        background: linear-gradient(180deg, #eef2ff 0%, var(--bg) 220px);
        color: var(--text);
        font-family: "Noto Sans CJK SC", "Source Han Sans CN", "Microsoft YaHei", sans-serif;
      }}
      .report-root {{
        max-width: 980px;
        margin: 0 auto;
        background: var(--card);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
        padding: 40px 44px;
      }}
      h1, h2, h3 {{
        color: #0f172a;
        line-height: 1.3;
        margin: 1.2em 0 0.55em;
      }}
      h1 {{
        margin-top: 0;
        font-size: 34px;
      }}
      h2 {{
        font-size: 24px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--line);
      }}
      h3 {{
        font-size: 18px;
      }}
      p, li, blockquote {{
        font-size: 15px;
        line-height: 1.85;
      }}
      ul {{
        padding-left: 1.4em;
      }}
      hr {{
        border: none;
        border-top: 1px solid var(--line);
        margin: 24px 0;
      }}
      blockquote {{
        margin: 16px 0;
        padding: 12px 16px;
        border-left: 4px solid var(--accent);
        background: var(--accent-soft);
        color: #1d4ed8;
        border-radius: 10px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin: 18px 0 24px;
        table-layout: fixed;
        overflow: hidden;
        border-radius: 14px;
      }}
      thead th, th {{
        background: #f1f5f9;
        color: #0f172a;
        font-weight: 700;
      }}
      th, td {{
        border: 1px solid var(--line);
        padding: 12px 14px;
        text-align: left;
        vertical-align: top;
        font-size: 14px;
        line-height: 1.7;
        word-break: break-word;
      }}
      tr:nth-child(even) td {{
        background: #fcfdff;
      }}
      strong {{
        color: #0f172a;
      }}
      code {{
        font-family: "JetBrains Mono", "SFMono-Regular", monospace;
        background: #f8fafc;
        padding: 2px 6px;
        border-radius: 6px;
      }}
    </style>
  </head>
  <body>
    <main class="report-root">
      {body}
    </main>
  </body>
</html>"""

    def _normalize_markdown(self, markdown: str) -> str:
        content = markdown.strip()
        fenced = re.fullmatch(r"```(?:markdown)?\s*(.*?)\s*```", content, flags=re.DOTALL)
        if fenced:
            content = fenced.group(1).strip()
        return content
