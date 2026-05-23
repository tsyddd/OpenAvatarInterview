from __future__ import annotations

from pydantic import BaseModel

from .emotion_types import EmotionAssessment, EmotionState, EmotionStrategy


class InterviewPolicy(BaseModel):
    question_mode: str
    topic_shift: bool
    difficulty_delta: int
    tone: str
    followup_allowed: bool


def build_interview_policy(
    state: EmotionState,
    strategy: EmotionStrategy,
) -> InterviewPolicy:
    if state == EmotionState.ANXIOUS:
        if strategy == EmotionStrategy.DECOMPRESS:
            return InterviewPolicy(
                question_mode="light_related",
                topic_shift=True,
                difficulty_delta=-2,
                tone="supportive",
                followup_allowed=False,
            )
        return InterviewPolicy(
            question_mode="same_topic_simplified",
            topic_shift=False,
            difficulty_delta=-1,
            tone="gentle",
            followup_allowed=False,
        )

    if state == EmotionState.CONFIDENT:
        if strategy == EmotionStrategy.PROBE_EVIDENCE:
            return InterviewPolicy(
                question_mode="evidence_probe",
                topic_shift=False,
                difficulty_delta=0,
                tone="neutral",
                followup_allowed=True,
            )
        return InterviewPolicy(
            question_mode="deepening",
            topic_shift=False,
            difficulty_delta=1,
            tone="neutral",
            followup_allowed=True,
        )

    if strategy == EmotionStrategy.PROBE_EVIDENCE:
        return InterviewPolicy(
            question_mode="clarify_with_examples",
            topic_shift=False,
            difficulty_delta=0,
            tone="neutral",
            followup_allowed=True,
        )
    if strategy == EmotionStrategy.DECOMPRESS:
        return InterviewPolicy(
            question_mode="light_related",
            topic_shift=True,
            difficulty_delta=-1,
            tone="supportive",
            followup_allowed=False,
        )
    if strategy == EmotionStrategy.REDUCE_DIFFICULTY:
        return InterviewPolicy(
            question_mode="same_topic_simplified",
            topic_shift=False,
            difficulty_delta=-1,
            tone="neutral",
            followup_allowed=True,
        )
    return InterviewPolicy(
        question_mode="normal_followup",
        topic_shift=False,
        difficulty_delta=0,
        tone="neutral",
        followup_allowed=True,
    )


def build_interview_policy_from_assessment(assessment: EmotionAssessment) -> InterviewPolicy:
    return build_interview_policy(assessment.state, assessment.strategy)

