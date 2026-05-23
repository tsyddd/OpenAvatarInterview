from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, TypedDict

from loguru import logger
from openai import OpenAI

from ..interview_config import InterviewAgentConfig
from ..prompts.loader import PromptLoader
from .emotion_features import EmotionFeatureExtractor
from .emotion_prompt import build_emotion_system_prompt, build_emotion_user_prompt
from .emotion_types import (
    EmotionAssessment,
    EmotionAssessmentInput,
    EmotionFeatureSummary,
    EmotionState,
    EmotionStrategy,
    RiskLevel,
)

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = "__end__"
    StateGraph = None


class EmotionPayload(TypedDict, total=False):
    data: EmotionAssessmentInput
    features: EmotionFeatureSummary
    assessment: EmotionAssessment


def temporal_smooth_state(history: list[EmotionState | str]) -> EmotionState:
    normalized = [item if isinstance(item, EmotionState) else EmotionState(str(item)) for item in history if item]
    if not normalized:
        return EmotionState.STABLE
    recent = normalized[-3:]
    if len(recent) >= 2 and recent[-1] == EmotionState.ANXIOUS and recent[-2] == EmotionState.ANXIOUS:
        return EmotionState.ANXIOUS
    if len(recent) >= 2 and recent[-1] == EmotionState.CONFIDENT and recent[-2] == EmotionState.CONFIDENT:
        return EmotionState.CONFIDENT
    if recent[-1] == EmotionState.ANXIOUS:
        return EmotionState.STABLE
    if recent[-1] == EmotionState.CONFIDENT and recent.count(EmotionState.CONFIDENT) >= 2:
        return EmotionState.CONFIDENT
    return recent[-1]


class EmotionAgent:
    def __init__(self, config: InterviewAgentConfig, client: OpenAI | None):
        self.config = config
        self.client = client
        self.prompts = PromptLoader(Path(__file__).resolve().parents[1] / "prompts")
        self.extractor = EmotionFeatureExtractor()
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(EmotionPayload)
        graph.add_node("extract_features", self._extract_features)
        graph.add_node("assess_emotion", self._assess_emotion)
        graph.add_edge("extract_features", "assess_emotion")
        graph.add_edge("assess_emotion", END)
        graph.set_entry_point("extract_features")
        return graph.compile()

    def assess(self, data: EmotionAssessmentInput) -> EmotionAssessment:
        payload: EmotionPayload = {"data": data}
        result = self.graph.invoke(payload) if self.graph is not None else self._assess_emotion(self._extract_features(payload))
        assessment = result.get("assessment") or self._fallback_assessment(data, self.extractor.extract(data))
        if data.previous_states:
            smoothed = temporal_smooth_state([*data.previous_states[-2:], assessment.state])
            if smoothed != assessment.state:
                assessment = self._apply_smoothed_state(assessment, smoothed)
        return assessment

    def assess_rules_only(self, data: EmotionAssessmentInput) -> EmotionAssessment:
        features = self.extractor.extract(data)
        assessment = self._fallback_assessment(data, features)
        if data.previous_states:
            smoothed = temporal_smooth_state([*data.previous_states[-2:], assessment.state])
            if smoothed != assessment.state:
                assessment = self._apply_smoothed_state(assessment, smoothed)
        return assessment

    def _extract_features(self, payload: EmotionPayload) -> EmotionPayload:
        data = payload["data"]
        payload["features"] = self.extractor.extract(data)
        return payload

    def _assess_emotion(self, payload: EmotionPayload) -> EmotionPayload:
        data = payload["data"]
        features = payload["features"]
        fallback = self._fallback_assessment(data, features)
        if self.client is None:
            payload["assessment"] = fallback
            return payload

        try:
            response = self.client.chat.completions.create(
                model=getattr(self.config, "emotion_model_name", self.config.dialogue_analyzer_model),
                messages=[
                    {"role": "system", "content": build_emotion_system_prompt()},
                    {"role": "user", "content": build_emotion_user_prompt(data, features)},
                ],
                stream=False,
                response_format={"type": "json_object"},
                max_tokens=900,
            )
            content = response.choices[0].message.content if response and response.choices else "{}"
            parsed = json.loads(self._extract_json(content or "{}"))
            assessment = EmotionAssessment.model_validate(parsed)
            payload["assessment"] = self._postprocess_assessment(assessment, data, features)
        except Exception as exc:
            logger.warning(f"EmotionAgent LLM output invalid, using fallback: {type(exc).__name__}: {exc}")
            payload["assessment"] = fallback
        return payload

    def _postprocess_assessment(
        self,
        assessment: EmotionAssessment,
        data: EmotionAssessmentInput,
        features: EmotionFeatureSummary,
    ) -> EmotionAssessment:
        if not assessment.signals:
            assessment.signals = self._build_feature_signals(data, features)
        if assessment.confidence < 0.0 or assessment.confidence > 1.0:
            assessment.confidence = 0.5
        return assessment

    def _fallback_assessment(
        self,
        data: EmotionAssessmentInput,
        features: EmotionFeatureSummary,
    ) -> EmotionAssessment:
        short_answer = features.answer_length < 12
        anxious_score = (
            features.uncertain_terms_count * 1.2
            + features.self_negation_count * 1.5
            + features.avoidance_terms_count * 1.3
            + features.emotional_cue_count * 1.5
            - features.direct_answer_score * 1.2
            - features.detail_density * 0.8
        )
        confident_score = (
            features.direct_answer_score * 2.0
            + features.detail_density * 1.6
            + min(features.technical_term_count, 6) * 0.18
            + min(features.numeric_detail_count, 4) * 0.08
            - features.uncertain_terms_count * 0.4
            - features.self_negation_count * 0.6
        )

        if short_answer and features.direct_answer_score >= 0.45 and anxious_score < 2.2:
            state = EmotionState.STABLE
        elif anxious_score >= 3.0:
            state = EmotionState.ANXIOUS
        elif confident_score >= 2.2:
            state = EmotionState.CONFIDENT
        else:
            state = EmotionState.STABLE

        if state == EmotionState.ANXIOUS:
            strategy = EmotionStrategy.DECOMPRESS if anxious_score >= 4.0 else EmotionStrategy.REDUCE_DIFFICULTY
            risk = RiskLevel.HIGH if anxious_score >= 4.0 else RiskLevel.MEDIUM
            hint = "候选人有明显不确定或自我否定信号，先降低压迫感，不要继续高压追问。"
            transition = "没关系，我们先放轻松一点。你可以从自己最熟悉、最有把握的部分开始讲。"
            confidence = min(0.9, 0.45 + anxious_score / 8.0)
        elif state == EmotionState.CONFIDENT:
            strategy = EmotionStrategy.CONTINUE_DEEPENING if features.detail_density >= 0.45 else EmotionStrategy.PROBE_EVIDENCE
            risk = RiskLevel.LOW
            hint = "候选人表达稳定且有技术细节，可以围绕当前点继续深挖。"
            transition = "你刚才这部分讲得比较清楚，我们沿着这个点再往下展开一层。"
            confidence = min(0.92, 0.5 + confident_score / 6.0)
        else:
            strategy = EmotionStrategy.PROBE_EVIDENCE if features.direct_answer_score < 0.45 else EmotionStrategy.REDUCE_DIFFICULTY
            risk = RiskLevel.MEDIUM if short_answer or features.avoidance_terms_count > 0 else RiskLevel.LOW
            hint = "当前状态基本平稳，但证据不够充分时先用温和方式补具体例子。"
            transition = "可以的。你先结合一个具体场景，按当时的做法再展开一点。"
            confidence = 0.5 if short_answer else 0.62

        return EmotionAssessment(
            state=state,
            confidence=max(0.0, min(1.0, confidence)),
            signals=self._build_feature_signals(data, features),
            risk_level=risk,
            strategy=strategy,
            interviewer_hint=hint,
            suggested_transition=transition,
        )

    def _apply_smoothed_state(self, assessment: EmotionAssessment, smoothed: EmotionState) -> EmotionAssessment:
        if smoothed == assessment.state:
            return assessment
        if smoothed == EmotionState.STABLE and assessment.state == EmotionState.ANXIOUS:
            assessment.state = EmotionState.STABLE
            assessment.strategy = EmotionStrategy.REDUCE_DIFFICULTY
            assessment.risk_level = RiskLevel.MEDIUM
            assessment.interviewer_hint = "上一轮出现了紧张信号，但尚未连续出现，先温和降难度，不必立刻大幅切题。"
        elif smoothed == EmotionState.CONFIDENT:
            assessment.state = EmotionState.CONFIDENT
            assessment.strategy = EmotionStrategy.CONTINUE_DEEPENING
            assessment.risk_level = RiskLevel.LOW
        return assessment

    def _build_feature_signals(
        self,
        data: EmotionAssessmentInput,
        features: EmotionFeatureSummary,
    ) -> list[str]:
        signals: list[str] = []
        if features.uncertain_terms_count:
            signals.append(f"出现不确定表达 {features.uncertain_terms_count} 次")
        if features.self_negation_count:
            signals.append(f"出现自我否定表达 {features.self_negation_count} 次")
        if features.avoidance_terms_count:
            signals.append(f"出现回避表达 {features.avoidance_terms_count} 次")
        if features.technical_term_count:
            signals.append(f"技术术语较多，共 {features.technical_term_count} 个")
        if features.detail_density >= 0.45:
            signals.append(f"细节密度较高，detail_density={features.detail_density:.2f}")
        if features.direct_answer_score >= 0.6:
            signals.append(f"回答直接度较高，direct_answer_score={features.direct_answer_score:.2f}")
        if not signals:
            signals.append(f"回答长度较短，answer_length={features.answer_length}")
        if data.candidate_answer.strip():
            signals.append(f"本轮回答摘录：{data.candidate_answer.strip()[:48]}")
        return signals[:5]

    @staticmethod
    def _extract_json(text: str) -> str:
        cleaned = text.strip()
        fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        return cleaned
