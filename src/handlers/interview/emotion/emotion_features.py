from __future__ import annotations

import re
from collections.abc import Iterable

from .emotion_types import EmotionAssessmentInput, EmotionFeatureSummary


class EmotionFeatureExtractor:
    UNCERTAIN_TERMS = (
        "不太确定", "不确定", "可能", "也许", "大概", "应该", "差不多", "记不清", "忘了",
        "不太清楚", "说不好", "不一定", "好像", "似乎", "我猜", "可能吧",
    )
    SELF_NEGATION_TERMS = (
        "我不会", "我不行", "我不太会", "我没做过", "我做得不好", "我讲不好", "我讲不清楚",
        "我比较差", "我不擅长", "我能力一般", "我没有准备好", "我不懂", "没怎么做过", "没做太多",
    )
    AVOIDANCE_TERMS = (
        "这个先不说", "跳过", "不太方便说", "没什么好说", "不展开了", "没细看",
        "没深入", "只是简单了解", "不记得了", "没关注", "没有特别多",
    )
    ABSOLUTIST_TERMS = ("一定", "绝对", "完全", "从来", "从不", "肯定", "必须", "全部", "一点都不")
    EMOTIONAL_CUES = ("紧张", "焦虑", "担心", "害怕", "压力", "怕答错", "有点慌", "心里没底")
    DIRECT_ANSWER_MARKERS = ("我认为", "我会", "我的做法是", "核心是", "首先", "第一", "直接说结论", "结论是")
    EXAMPLE_MARKERS = ("例如", "比如", "举个例子", "一次", "当时", "后来", "最终", "具体来说")
    TECHNICAL_TERMS = (
        "python", "java", "golang", "redis", "mysql", "postgresql", "kafka", "mq", "es", "elasticsearch",
        "docker", "kubernetes", "grpc", "http", "tcp", "缓存", "索引", "线程", "协程", "锁", "事务",
        "分布式", "微服务", "网关", "监控", "告警", "压测", "限流", "降级", "熔断", "重试",
        "幂等", "容器", "sql", "接口", "架构", "部署", "日志", "链路追踪", "一致性", "延迟",
    )

    SENTENCE_SPLIT_RE = re.compile(r"[。！？!?；;]+")
    NUMERIC_RE = re.compile(r"\d+")

    def extract(self, data: EmotionAssessmentInput) -> EmotionFeatureSummary:
        answer = self._normalize_text(data.candidate_answer)
        history_text = self._normalize_text(" ".join(turn.text for turn in data.recent_history[-4:] if turn.role == "candidate"))
        combined = f"{history_text} {answer}".strip()
        base_text = answer or combined

        sentence_count = self._count_sentences(base_text)
        answer_length = len(re.sub(r"\s+", "", answer))
        technical_term_count = self._count_keywords(base_text.lower(), self.TECHNICAL_TERMS)
        example_marker_count = self._count_keywords(base_text, self.EXAMPLE_MARKERS)
        numeric_detail_count = len(self.NUMERIC_RE.findall(base_text))

        direct_answer_score = self._compute_direct_answer_score(answer, data.current_question)
        detail_density = self._compute_detail_density(
            answer_length=answer_length,
            sentence_count=sentence_count,
            technical_term_count=technical_term_count,
            example_marker_count=example_marker_count,
            numeric_detail_count=numeric_detail_count,
        )

        return EmotionFeatureSummary(
            uncertain_terms_count=self._count_keywords(base_text, self.UNCERTAIN_TERMS),
            self_negation_count=self._count_keywords(base_text, self.SELF_NEGATION_TERMS),
            avoidance_terms_count=self._count_keywords(base_text, self.AVOIDANCE_TERMS),
            absolutist_terms_count=self._count_keywords(base_text, self.ABSOLUTIST_TERMS),
            answer_length=answer_length,
            sentence_count=sentence_count,
            technical_term_count=technical_term_count,
            detail_density=detail_density,
            direct_answer_score=direct_answer_score,
            example_marker_count=example_marker_count,
            numeric_detail_count=numeric_detail_count,
            emotional_cue_count=self._count_keywords(base_text, self.EMOTIONAL_CUES),
        )

    def summarize_for_prompt(self, features: EmotionFeatureSummary) -> str:
        return (
            f"uncertain_terms_count={features.uncertain_terms_count}, "
            f"self_negation_count={features.self_negation_count}, "
            f"avoidance_terms_count={features.avoidance_terms_count}, "
            f"absolutist_terms_count={features.absolutist_terms_count}, "
            f"answer_length={features.answer_length}, "
            f"sentence_count={features.sentence_count}, "
            f"technical_term_count={features.technical_term_count}, "
            f"detail_density={features.detail_density:.2f}, "
            f"direct_answer_score={features.direct_answer_score:.2f}, "
            f"example_marker_count={features.example_marker_count}, "
            f"numeric_detail_count={features.numeric_detail_count}, "
            f"emotional_cue_count={features.emotional_cue_count}"
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "")).strip()

    def _count_keywords(self, text: str, keywords: Iterable[str]) -> int:
        total = 0
        for keyword in keywords:
            total += text.count(keyword)
        return total

    def _count_sentences(self, text: str) -> int:
        if not text:
            return 0
        parts = [part for part in self.SENTENCE_SPLIT_RE.split(text) if part.strip()]
        return max(1, len(parts))

    def _compute_direct_answer_score(self, answer: str, current_question: str) -> float:
        if not answer:
            return 0.2
        score = 0.0
        lowered = answer.lower()
        if any(marker in answer for marker in self.DIRECT_ANSWER_MARKERS):
            score += 0.35
        if len(answer) >= 40:
            score += 0.15
        if self._count_sentences(answer) >= 2:
            score += 0.15
        if self.NUMERIC_RE.search(answer):
            score += 0.1
        if any(term in lowered for term in self.TECHNICAL_TERMS):
            score += 0.15
        if current_question and any(token in answer for token in self._question_tokens(current_question)):
            score += 0.1
        if any(term in answer for term in self.UNCERTAIN_TERMS):
            score -= 0.15
        return max(0.0, min(1.0, score))

    def _compute_detail_density(
        self,
        *,
        answer_length: int,
        sentence_count: int,
        technical_term_count: int,
        example_marker_count: int,
        numeric_detail_count: int,
    ) -> float:
        if answer_length <= 0:
            return 0.0
        density = (
            min(technical_term_count, 6) * 0.10
            + min(example_marker_count, 4) * 0.12
            + min(numeric_detail_count, 5) * 0.08
            + min(sentence_count, 5) * 0.05
            + min(answer_length / 120.0, 0.25)
        )
        return max(0.0, min(1.0, density))

    @staticmethod
    def _question_tokens(question: str) -> list[str]:
        tokens = [token for token in re.split(r"[，。！？、\s]+", question) if len(token) >= 2]
        return tokens[:8]
