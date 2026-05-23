from __future__ import annotations

import json

from .emotion_types import EmotionAssessmentInput, EmotionFeatureSummary


def build_emotion_system_prompt() -> str:
    return (
        "你是一个用于模拟面试系统的 EmotionAgent。\n"
        "你的任务不是做医学或临床心理诊断，也不能输出任何疾病标签。\n"
        "你只评估候选人在当前面试交互中的状态，用于帮助 InterviewerAgent 调整下一轮提问策略。\n"
        "你只能输出以下 state 之一：stable, anxious, confident。\n"
        "你只能输出以下 strategy 之一：continue_deepening, decompress, reduce_difficulty, probe_evidence。\n"
        "请结合当前问题、候选人回答、最近对话历史、可选简历摘要，以及规则特征摘要进行判断。\n"
        "如果候选人显得紧张、不确定、自我否定、回答收缩，倾向 anxious，并建议 decompress 或 reduce_difficulty。\n"
        "如果候选人表达直接、结构清晰、技术细节具体，倾向 confident，并建议 continue_deepening 或 probe_evidence。\n"
        "如果证据不充分，优先输出 stable，不要过度推断。\n"
        "必须严格返回 JSON，不要返回 markdown，不要解释。"
    )


def build_emotion_user_prompt(data: EmotionAssessmentInput, features: EmotionFeatureSummary) -> str:
    history = [
        {"role": turn.role, "text": turn.text}
        for turn in data.recent_history[-4:]
    ]
    payload = {
        "current_question": data.current_question,
        "candidate_answer": data.candidate_answer,
        "recent_history": history,
        "candidate_profile_summary": data.candidate_profile_summary or "",
        "feature_summary": features.to_prompt_dict(),
        "required_json_schema": {
            "state": "stable|anxious|confident",
            "confidence": 0.0,
            "signals": ["字符串1", "字符串2"],
            "risk_level": "low|medium|high",
            "strategy": "continue_deepening|decompress|reduce_difficulty|probe_evidence",
            "interviewer_hint": "字符串",
            "suggested_transition": "字符串",
        },
    }
    return (
        "请根据以下输入，输出严格 JSON。\n"
        "注意：risk_level 仅表示当前面试交互风险，不代表医学风险。\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

