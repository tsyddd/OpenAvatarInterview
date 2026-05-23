from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EmotionState(StrEnum):
    STABLE = "stable"
    ANXIOUS = "anxious"
    CONFIDENT = "confident"


class EmotionStrategy(StrEnum):
    CONTINUE_DEEPENING = "continue_deepening"
    DECOMPRESS = "decompress"
    REDUCE_DIFFICULTY = "reduce_difficulty"
    PROBE_EVIDENCE = "probe_evidence"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DialogueTurn(BaseModel):
    role: str
    text: str


class EmotionAssessmentInput(BaseModel):
    current_question: str = Field(default="")
    candidate_answer: str = Field(default="")
    recent_history: list[DialogueTurn] = Field(default_factory=list)
    candidate_profile_summary: str | None = None
    previous_states: list[EmotionState] = Field(default_factory=list)


class EmotionFeatureSummary(BaseModel):
    uncertain_terms_count: int = 0
    self_negation_count: int = 0
    avoidance_terms_count: int = 0
    absolutist_terms_count: int = 0
    answer_length: int = 0
    sentence_count: int = 0
    technical_term_count: int = 0
    detail_density: float = 0.0
    direct_answer_score: float = 0.0
    example_marker_count: int = 0
    numeric_detail_count: int = 0
    emotional_cue_count: int = 0

    def to_prompt_dict(self) -> dict[str, Any]:
        return self.model_dump()


class EmotionAssessment(BaseModel):
    state: EmotionState
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    strategy: EmotionStrategy = EmotionStrategy.REDUCE_DIFFICULTY
    interviewer_hint: str = Field(default="")
    suggested_transition: str = Field(default="")

    @field_validator("signals", mode="before")
    @classmethod
    def _normalize_signals(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return [str(value)]

