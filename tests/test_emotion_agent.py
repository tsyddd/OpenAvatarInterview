from handlers.interview.emotion.emotion_agent import EmotionAgent, temporal_smooth_state
from handlers.interview.emotion.emotion_features import EmotionFeatureExtractor
from handlers.interview.emotion.emotion_types import (
    DialogueTurn,
    EmotionAssessmentInput,
    EmotionState,
    EmotionStrategy,
)
from handlers.interview.emotion.interview_policy import build_interview_policy
from handlers.interview.interview_config import InterviewAgentConfig


class _MockMessage:
    def __init__(self, content: str):
        self.content = content


class _MockChoice:
    def __init__(self, content: str):
        self.message = _MockMessage(content)


class _MockResponse:
    def __init__(self, content: str):
        self.choices = [_MockChoice(content)]


class _MockCompletions:
    def __init__(self, content: str):
        self._content = content

    def create(self, **kwargs):
        return _MockResponse(self._content)


class _MockChat:
    def __init__(self, content: str):
        self.completions = _MockCompletions(content)


class _MockClient:
    def __init__(self, content: str):
        self.chat = _MockChat(content)


def _build_input(answer: str) -> EmotionAssessmentInput:
    return EmotionAssessmentInput(
        current_question="请介绍一下你主导的项目。",
        candidate_answer=answer,
        recent_history=[
            DialogueTurn(role="interviewer", text="请介绍一下你主导的项目。"),
            DialogueTurn(role="candidate", text=answer),
        ],
        candidate_profile_summary="候选人有三年后端开发经验。",
    )


def test_feature_extractor_detects_anxious_language():
    extractor = EmotionFeatureExtractor()
    features = extractor.extract(_build_input("我有点紧张，这块其实不太确定，可能没怎么做过，也说不太清楚。"))

    assert features.uncertain_terms_count >= 2
    assert features.self_negation_count >= 1
    assert features.direct_answer_score < 0.6


def test_emotion_agent_falls_back_on_invalid_json():
    agent = EmotionAgent(InterviewAgentConfig(), _MockClient("not-json"))
    result = agent.assess(_build_input("这个我不太确定，可能没有做得很好。"))

    assert result.state in {EmotionState.STABLE, EmotionState.ANXIOUS}
    assert result.strategy in {
        EmotionStrategy.REDUCE_DIFFICULTY,
        EmotionStrategy.DECOMPRESS,
        EmotionStrategy.PROBE_EVIDENCE,
        EmotionStrategy.CONTINUE_DEEPENING,
    }
    assert result.signals


def test_temporal_smoothing_requires_repetition_for_escalation():
    assert temporal_smooth_state(
        [EmotionState.STABLE, EmotionState.ANXIOUS, EmotionState.STABLE]
    ) == EmotionState.STABLE
    assert temporal_smooth_state(
        [EmotionState.STABLE, EmotionState.ANXIOUS, EmotionState.ANXIOUS]
    ) == EmotionState.ANXIOUS
    assert temporal_smooth_state(
        [EmotionState.STABLE, EmotionState.CONFIDENT, EmotionState.CONFIDENT]
    ) == EmotionState.CONFIDENT


def test_interview_policy_maps_anxious_to_lower_pressure():
    policy = build_interview_policy(EmotionState.ANXIOUS, EmotionStrategy.DECOMPRESS)

    assert policy.followup_allowed is False
    assert policy.difficulty_delta <= 0
    assert policy.tone in {"supportive", "gentle"}
