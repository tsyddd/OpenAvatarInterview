from __future__ import annotations

import io
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class ReportPdfRenderer:
    PAGE_SIZE = (1240, 1754)
    MARGIN_X = 96
    MARGIN_Y = 96
    LINE_GAP = 14
    TITLE_GAP = 24
    BODY_FONT_SIZE = 28
    TITLE_FONT_SIZE = 42
    SUBTITLE_FONT_SIZE = 34
    SMALL_FONT_SIZE = 24
    TABLE_CELL_PADDING_X = 14
    TABLE_CELL_PADDING_Y = 10
    FONT_CANDIDATES = (
        Path("/home/liang/.fonts/SimHei.ttf"),
        Path("/usr/share/fonts/truetype/思源黑体/SourceHanSansCN-Medium.otf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"),
        Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    )

    def render(self, markdown: str) -> bytes:
        title_font = self._load_font(self.TITLE_FONT_SIZE)
        subtitle_font = self._load_font(self.SUBTITLE_FONT_SIZE)
        body_font = self._load_font(self.BODY_FONT_SIZE)
        small_font = self._load_font(self.SMALL_FONT_SIZE)
        bold_body_font = self._load_font(self.BODY_FONT_SIZE, bold=True)
        normalized = self._normalize_markdown(markdown or "面试报告暂无内容。")
        blocks = self._parse_blocks(normalized)
        pages = self._render_pages(blocks, title_font, subtitle_font, body_font, small_font, bold_body_font)
        buffer = io.BytesIO()
        first, rest = pages[0], pages[1:]
        first.save(buffer, format="PDF", save_all=True, append_images=rest, resolution=150.0)
        return buffer.getvalue()

    def _normalize_markdown(self, markdown: str) -> str:
        content = markdown.strip()
        fenced = re.fullmatch(r"```(?:markdown)?\s*(.*?)\s*```", content, flags=re.DOTALL)
        if fenced:
            content = fenced.group(1).strip()
        content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
        content = re.sub(r"__(.*?)__", r"\1", content)
        return content

    def _parse_blocks(self, markdown: str) -> list[dict]:
        lines = markdown.splitlines()
        blocks: list[dict] = []
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            stripped = line.strip()
            if not stripped:
                blocks.append({"type": "blank"})
                i += 1
                continue
            if stripped.startswith("|") and self._is_table_line(stripped):
                table_lines = [stripped]
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                rows = self._parse_table_rows(table_lines)
                if rows:
                    blocks.append({"type": "table", "rows": rows})
                continue
            if re.fullmatch(r"[-*_]{3,}", stripped):
                blocks.append({"type": "divider"})
                i += 1
                continue
            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                blocks.append({"type": "heading", "level": min(level, 3), "text": stripped.lstrip("#").strip()})
                i += 1
                continue
            if stripped.startswith(">"):
                blocks.append({"type": "quote", "text": stripped.lstrip(">").strip()})
                i += 1
                continue
            if stripped.startswith("- ") or stripped.startswith("* "):
                blocks.append({"type": "bullet", "text": stripped[2:].strip()})
                i += 1
                continue
            blocks.append({"type": "paragraph", "text": stripped})
            i += 1
        return blocks

    def _render_pages(
        self,
        blocks: list[dict],
        title_font: ImageFont.ImageFont,
        subtitle_font: ImageFont.ImageFont,
        body_font: ImageFont.ImageFont,
        small_font: ImageFont.ImageFont,
        bold_body_font: ImageFont.ImageFont,
    ) -> list[Image.Image]:
        pages: list[Image.Image] = []
        page = Image.new("RGB", self.PAGE_SIZE, "white")
        draw = ImageDraw.Draw(page)
        y = self.MARGIN_Y
        content_width = self.PAGE_SIZE[0] - self.MARGIN_X * 2

        for block in blocks:
            block_type = block["type"]
            if block_type == "blank":
                y = self._advance_blank(y, body_font, pages, page, draw)
                if y is None:
                    page = pages.pop()
                continue
            if block_type == "divider":
                page, draw, y = self._ensure_space(page, draw, y, 30, pages)
                draw.line(
                    [(self.MARGIN_X, y + 10), (self.PAGE_SIZE[0] - self.MARGIN_X, y + 10)],
                    fill=(203, 213, 225),
                    width=2,
                )
                y += 28
                continue
            if block_type == "table":
                page, draw, y = self._draw_table(page, draw, y, block["rows"], small_font, pages, content_width)
                y += self.LINE_GAP
                continue

            text = block.get("text", "")
            if block_type == "heading":
                if block["level"] == 1:
                    font = title_font
                    fill = (15, 23, 42)
                else:
                    font = subtitle_font
                    fill = (30, 41, 59)
                indent = 0
            elif block_type == "bullet":
                font = body_font
                fill = (51, 65, 85)
                text = f"• {text}"
                indent = 0
            elif block_type == "quote":
                font = small_font
                fill = (71, 85, 105)
                text = f"引用：{text}"
                indent = 28
            else:
                font = bold_body_font if "综合得分：" in text else body_font
                fill = (51, 65, 85)
                indent = 0

            wrapped_lines = self._wrap_text(text, font, draw, content_width - indent)
            for wrapped in wrapped_lines:
                bbox = draw.textbbox((0, 0), wrapped, font=font)
                line_height = (bbox[3] - bbox[1]) + self.LINE_GAP
                page, draw, y = self._ensure_space(page, draw, y, line_height, pages)
                draw.text((self.MARGIN_X + indent, y), wrapped, font=font, fill=fill)
                y += line_height
            y += self.TITLE_GAP if block_type == "heading" else self.LINE_GAP

        pages.append(page)
        return pages

    def _draw_table(
        self,
        page: Image.Image,
        draw: ImageDraw.ImageDraw,
        y: int,
        rows: list[list[str]],
        font: ImageFont.ImageFont,
        pages: list[Image.Image],
        content_width: int,
    ) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
        col_count = max(len(row) for row in rows)
        col_width = content_width // max(col_count, 1)
        for row_index, row in enumerate(rows):
            normalized_row = row + [""] * (col_count - len(row))
            cell_heights = []
            wrapped_cells: list[list[str]] = []
            for cell in normalized_row:
                wrapped = self._wrap_text(cell, font, draw, col_width - self.TABLE_CELL_PADDING_X * 2)
                wrapped_cells.append(wrapped)
                cell_heights.append(len(wrapped) * (self.SMALL_FONT_SIZE + self.LINE_GAP) + self.TABLE_CELL_PADDING_Y * 2)
            row_height = max(cell_heights) if cell_heights else self.SMALL_FONT_SIZE + self.TABLE_CELL_PADDING_Y * 2
            page, draw, y = self._ensure_space(page, draw, y, row_height + 2, pages)
            x = self.MARGIN_X
            for col_index, wrapped in enumerate(wrapped_cells):
                x2 = x + col_width
                fill = (241, 245, 249) if row_index == 0 else (255, 255, 255)
                draw.rectangle([(x, y), (x2, y + row_height)], outline=(203, 213, 225), fill=fill, width=2)
                text_y = y + self.TABLE_CELL_PADDING_Y
                for line in wrapped:
                    draw.text((x + self.TABLE_CELL_PADDING_X, text_y), line, font=font, fill=(51, 65, 85))
                    text_y += self.SMALL_FONT_SIZE + self.LINE_GAP
                x = x2
            y += row_height
        return page, draw, y

    def _advance_blank(
        self,
        y: int,
        font: ImageFont.ImageFont,
        pages: list[Image.Image],
        page: Image.Image,
        draw: ImageDraw.ImageDraw,
    ) -> int | None:
        bbox = draw.textbbox((0, 0), "空", font=font)
        line_height = (bbox[3] - bbox[1]) + self.LINE_GAP
        if y + line_height > self.PAGE_SIZE[1] - self.MARGIN_Y:
            pages.append(page)
            return self.MARGIN_Y
        return y + line_height

    def _ensure_space(
        self,
        page: Image.Image,
        draw: ImageDraw.ImageDraw,
        y: int,
        height: int,
        pages: list[Image.Image],
    ) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
        if y + height <= self.PAGE_SIZE[1] - self.MARGIN_Y:
            return page, draw, y
        pages.append(page)
        page = Image.new("RGB", self.PAGE_SIZE, "white")
        draw = ImageDraw.Draw(page)
        y = self.MARGIN_Y
        return page, draw, y

    def _is_table_line(self, line: str) -> bool:
        return line.count("|") >= 2

    def _parse_table_rows(self, lines: list[str]) -> list[list[str]]:
        rows: list[list[str]] = []
        for idx, line in enumerate(lines):
            if idx == 1 and self._is_table_separator(line):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if any(cells):
                rows.append(cells)
        return rows

    def _is_table_separator(self, line: str) -> bool:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        return bool(cells) and all(cell and set(cell) <= {"-", ":"} for cell in cells)

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.ImageFont,
        draw: ImageDraw.ImageDraw,
        width: int,
    ) -> list[str]:
        wrapped: list[str] = []
        paragraph = text
        estimated = max(12, width // max(self.BODY_FONT_SIZE, 1))
        for chunk in textwrap.wrap(paragraph, width=estimated, break_long_words=True, replace_whitespace=False) or [paragraph]:
            current = chunk
            while draw.textlength(current, font=font) > width and len(current) > 1:
                split_at = max(1, len(current) - 1)
                while split_at > 1 and draw.textlength(current[:split_at], font=font) > width:
                    split_at -= 1
                wrapped.append(current[:split_at])
                current = current[split_at:]
            if current:
                wrapped.append(current)
        return wrapped or [text]

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        for path in self.FONT_CANDIDATES:
            if path.exists():
                try:
                    return ImageFont.truetype(str(path), size=size)
                except Exception:
                    continue
        return ImageFont.load_default()
