from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..models.interview_models import InterviewSessionState


class InterviewSessionRepository:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else Path("runtime/sessions")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        path = self.base_dir / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_state(self, session_id: str, state: InterviewSessionState) -> Path:
        path = self.session_dir(session_id) / "session.json"
        path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_state(self, session_id: str) -> InterviewSessionState | None:
        path = self.session_dir(session_id) / "session.json"
        if not path.exists():
            return None
        return InterviewSessionState.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def append_transcript(self, session_id: str, payload: dict[str, Any]) -> Path:
        path = self.session_dir(session_id) / "transcript.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return path

    def save_resume_file(self, session_id: str, source_path: Path, filename: str | None = None) -> Path:
        target_name = filename or source_path.name
        target_path = self.session_dir(session_id) / target_name
        if source_path.resolve() == target_path.resolve():
            return target_path
        shutil.copy2(source_path, target_path)
        return target_path

    def save_resume_text(self, session_id: str, text: str, filename: str = "resume_text.md") -> Path:
        path = self.session_dir(session_id) / filename
        path.write_text(text, encoding="utf-8")
        return path

    def save_evaluation(self, session_id: str, payload: dict[str, Any]) -> Path:
        path = self.session_dir(session_id) / "evaluation.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_report_markdown(self, session_id: str, content: str) -> Path:
        path = self.session_dir(session_id) / "report.md"
        path.write_text(content, encoding="utf-8")
        return path

    def save_report_html(self, session_id: str, content: str, filename: str = "report.html") -> Path:
        path = self.session_dir(session_id) / filename
        path.write_text(content, encoding="utf-8")
        return path

    def save_report_json(self, session_id: str, payload: dict[str, Any]) -> Path:
        path = self.session_dir(session_id) / "report.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_report_pdf(self, session_id: str, content: bytes, filename: str = "report.pdf") -> Path:
        path = self.session_dir(session_id) / filename
        path.write_bytes(content)
        return path
