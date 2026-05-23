from __future__ import annotations

from .emotion_types import EmotionAssessment
from .interview_policy import InterviewPolicy


def build_interviewer_context_with_emotion(
    assessment: EmotionAssessment,
    policy: InterviewPolicy,
) -> str:
    return (
        "【交互状态辅助信息】\n"
        f"- 当前交互状态: {assessment.state.value}\n"
        f"- 建议策略: {assessment.strategy.value}\n"
        f"- 交互风险: {assessment.risk_level.value}\n"
        f"- 置信度: {assessment.confidence:.2f}\n"
        f"- 观察到的信号: {'；'.join(assessment.signals) if assessment.signals else '无明显信号'}\n"
        f"- 建议语气: {policy.tone}\n"
        f"- 问题模式: {policy.question_mode}\n"
        f"- 是否允许继续深挖: {'是' if policy.followup_allowed else '否'}\n"
        f"- 是否建议换更轻松的话题切入: {'是' if policy.topic_shift else '否'}\n"
        f"- 难度调整: {policy.difficulty_delta}\n"
        f"- 给面试官的内部提示: {assessment.interviewer_hint}\n"
        "请把这些信息作为提问风格约束使用，但不要逐字复述给候选人。"
    )


def build_next_question_policy_prompt(
    assessment: EmotionAssessment,
    policy: InterviewPolicy,
) -> str:
    return (
        "请基于以下交互状态来决定下一问的提问风格，不要直接生成最终问题内容：\n"
        f"1. 当前状态为 {assessment.state.value}，建议策略为 {assessment.strategy.value}。\n"
        f"2. question_mode={policy.question_mode}, topic_shift={policy.topic_shift}, "
        f"difficulty_delta={policy.difficulty_delta}, tone={policy.tone}, "
        f"followup_allowed={policy.followup_allowed}。\n"
        f"3. suggested_transition: {assessment.suggested_transition}\n"
        "4. 如果状态为 anxious，优先降低压迫感；如果状态为 confident，允许围绕当前技术点继续深入。"
    )

