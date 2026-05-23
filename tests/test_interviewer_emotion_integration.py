from handlers.interview.agents.interviewer_agent import InterviewerAgent
from handlers.interview.interview_config import InterviewAgentConfig
from handlers.interview.models.interview_models import InterviewSessionState, InterviewTurn


def test_interviewer_prompt_includes_emotion_context():
    agent = InterviewerAgent(InterviewAgentConfig())
    state = InterviewSessionState(
        session_id="s1",
        resume_summary="候选人有三年后端经验，做过检索和推荐。",
        current_question="请介绍一个你主导的项目。",
        turns=[
            InterviewTurn(role="interviewer", text="请介绍一个你主导的项目。"),
            InterviewTurn(role="candidate", text="我有点紧张，不过我主要负责检索服务。"),
        ],
        latest_fast_emotion_assessment={
            "state": "stable",
            "confidence": 0.41,
            "signals": ["回答较短"],
            "risk_level": "low",
            "strategy": "reduce_difficulty",
            "interviewer_hint": "先轻微降难度。",
            "suggested_transition": "先说最熟悉的一段。",
        },
        latest_refined_emotion_assessment={
            "state": "anxious",
            "confidence": 0.78,
            "signals": ["出现紧张表达"],
            "risk_level": "medium",
            "strategy": "decompress",
            "interviewer_hint": "先降低压迫感，再继续问相关经历。",
            "suggested_transition": "没关系，我们先聊你最熟悉的那部分。",
        },
        latest_emotion_assessment={
            "state": "anxious",
            "confidence": 0.78,
            "signals": ["出现紧张表达"],
            "risk_level": "medium",
            "strategy": "decompress",
            "interviewer_hint": "先降低压迫感，再继续问相关经历。",
            "suggested_transition": "没关系，我们先聊你最熟悉的那部分。",
        },
    )

    payload = agent.plan_turn(state, "我主要负责检索服务。")

    assert "交互状态辅助信息" in payload["prompt"]
    assert "当前交互状态: anxious" in payload["prompt"]
    assert "建议策略: decompress" in payload["prompt"]
    assert "给面试官的内部提示: 先降低压迫感，再继续问相关经历。" in payload["prompt"]
