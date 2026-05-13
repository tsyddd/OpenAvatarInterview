from __future__ import annotations

from pathlib import Path

from .document_loader import load_text_from_path


class ResumeParser:
    def parse(self, path: Path) -> str:
        return load_text_from_path(path)

    def summarize(self, text: str, max_chars: int = 1800) -> str:
        cleaned = " ".join(text.split())
        return cleaned[:max_chars]
