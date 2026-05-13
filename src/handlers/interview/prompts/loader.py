from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


class PromptLoader:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent

    def read(self, name: str) -> str:
        return (self.base_dir / name).read_text(encoding="utf-8")

    def render(self, name: str, variables: Mapping[str, Any] | None = None) -> str:
        content = self.read(name)
        for key, value in (variables or {}).items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content
