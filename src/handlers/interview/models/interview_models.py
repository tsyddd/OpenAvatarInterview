from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InterviewTurn:
    role: str
    text: str
    event: str = "turn"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterviewTurn":
        return cls(
            role=str(data.get("role", "")),
            text=str(data.get("text", "")),
            event=str(data.get("event", "turn")),
        )


@dataclass
class InterviewSessionState:
    session_id: str
    stage: str = "created"
    report_status: str = "idle"
    report_error: str | None = None
    report_pdf_filename: str | None = None
    report_html_filename: str | None = None
    resume_filename: str | None = None
    resume_text: str = ""
    resume_summary: str = ""
    resume_analysis: dict[str, Any] | None = None
    question_plan: list[str] = field(default_factory=list)
    question_plan_details: list[dict[str, Any]] = field(default_factory=list)
    current_question: str = ""
    current_question_index: int = 0
    current_followup_count: int = 0
    covered_topics: list[str] = field(default_factory=list)
    conversation_summary: str = ""
    turns: list[InterviewTurn] = field(default_factory=list)
    latest_fast_emotion_assessment: dict[str, Any] | None = None
    latest_refined_emotion_assessment: dict[str, Any] | None = None
    latest_emotion_assessment: dict[str, Any] | None = None
    latest_interview_policy: dict[str, Any] | None = None
    emotion_state_history: list[str] = field(default_factory=list)
    dialogue_analysis: dict[str, Any] | None = None
    final_evaluation: dict[str, Any] | None = None
    final_report: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterviewSessionState":
        return cls(
            session_id=str(data.get("session_id", "")),
            stage=str(data.get("stage", "created")),
            report_status=str(data.get("report_status", "idle")),
            report_error=data.get("report_error"),
            report_pdf_filename=data.get("report_pdf_filename"),
            report_html_filename=data.get("report_html_filename"),
            resume_filename=data.get("resume_filename"),
            resume_text=str(data.get("resume_text", "")),
            resume_summary=str(data.get("resume_summary", "")),
            resume_analysis=data.get("resume_analysis"),
            question_plan=list(data.get("question_plan", [])),
            question_plan_details=list(data.get("question_plan_details", [])),
            current_question=str(data.get("current_question", "")),
            current_question_index=int(data.get("current_question_index", 0) or 0),
            current_followup_count=int(data.get("current_followup_count", 0) or 0),
            covered_topics=list(data.get("covered_topics", [])),
            conversation_summary=str(data.get("conversation_summary", "")),
            turns=[InterviewTurn.from_dict(item) for item in data.get("turns", [])],
            latest_fast_emotion_assessment=data.get("latest_fast_emotion_assessment"),
            latest_refined_emotion_assessment=data.get("latest_refined_emotion_assessment"),
            latest_emotion_assessment=data.get("latest_emotion_assessment"),
            latest_interview_policy=data.get("latest_interview_policy"),
            emotion_state_history=[str(item) for item in data.get("emotion_state_history", [])],
            dialogue_analysis=data.get("dialogue_analysis"),
            final_evaluation=data.get("final_evaluation"),
            final_report=data.get("final_report"),
        )
