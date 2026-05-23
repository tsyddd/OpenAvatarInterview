from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from handlers.interview.emotion.emotion_agent import EmotionAgent
from handlers.interview.emotion.emotion_types import DialogueTurn, EmotionAssessmentInput
from handlers.interview.emotion.interview_policy import build_interview_policy_from_assessment
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
    def create(self, **kwargs):
        user_text = kwargs["messages"][-1]["content"]
        if "有点紧张" in user_text or "不太确定" in user_text:
            content = {
                "state": "anxious",
                "confidence": 0.84,
                "signals": ["出现明显不确定表达", "回答里有紧张线索"],
                "risk_level": "high",
                "strategy": "decompress",
                "interviewer_hint": "先缓和气氛，再问更轻一些但相关的问题。",
                "suggested_transition": "没关系，我们先从你最熟悉的一段经历开始聊。",
            }
        elif "kafka" in user_text or "幂等" in user_text:
            content = {
                "state": "confident",
                "confidence": 0.88,
                "signals": ["技术细节充分", "结构化回答明显"],
                "risk_level": "low",
                "strategy": "continue_deepening",
                "interviewer_hint": "可以沿着当前技术点深入问设计权衡。",
                "suggested_transition": "你刚才提到的方案挺具体，我们继续往设计取舍上深挖一下。",
            }
        else:
            content = {
                "state": "stable",
                "confidence": 0.63,
                "signals": ["回答有基本信息，但细节还不够"],
                "risk_level": "medium",
                "strategy": "probe_evidence",
                "interviewer_hint": "先补一个具体例子，再决定是否继续深挖。",
                "suggested_transition": "你可以结合一次实际场景，再具体讲讲当时是怎么做的吗？",
            }
        return _MockResponse(json.dumps(content, ensure_ascii=False))


class _MockChat:
    def __init__(self):
        self.completions = _MockCompletions()


class _MockClient:
    def __init__(self):
        self.chat = _MockChat()


def _sample_inputs() -> list[tuple[str, EmotionAssessmentInput]]:
    return [
        (
            "anxious",
            EmotionAssessmentInput(
                current_question="请讲一个你解决线上问题的例子。",
                candidate_answer="我有点紧张，这块其实不太确定，可能之前做过类似的，但细节记不太清了。",
                recent_history=[
                    DialogueTurn(role="interviewer", text="请讲一个你解决线上问题的例子。"),
                    DialogueTurn(role="candidate", text="我有点紧张，这块其实不太确定，可能之前做过类似的，但细节记不太清了。"),
                ],
                candidate_profile_summary="三年后端开发，参与过交易系统。",
            ),
        ),
        (
            "confident",
            EmotionAssessmentInput(
                current_question="你在项目里是如何保证消息不重复消费的？",
                candidate_answer="我们当时用 Kafka 做异步链路，消费端通过业务主键做幂等表校验，同时把重试次数和死信队列分开管理。",
                recent_history=[
                    DialogueTurn(role="interviewer", text="你在项目里是如何保证消息不重复消费的？"),
                    DialogueTurn(role="candidate", text="我们当时用 Kafka 做异步链路，消费端通过业务主键做幂等表校验，同时把重试次数和死信队列分开管理。"),
                ],
                candidate_profile_summary="熟悉高并发后端系统。",
            ),
        ),
        (
            "confused",
            EmotionAssessmentInput(
                current_question="请介绍一下你在压测方面的经验。",
                candidate_answer="做过一些压测，但我先说结论的话，主要还是看接口延迟和资源使用，具体例子我可以再想一下。",
                recent_history=[
                    DialogueTurn(role="interviewer", text="请介绍一下你在压测方面的经验。"),
                    DialogueTurn(role="candidate", text="做过一些压测，但我先说结论的话，主要还是看接口延迟和资源使用，具体例子我可以再想一下。"),
                ],
                candidate_profile_summary="有基础性能优化经验。",
            ),
        ),
    ]


def main() -> None:
    agent = EmotionAgent(InterviewAgentConfig(), _MockClient())
    for label, item in _sample_inputs():
        assessment = agent.assess(item)
        policy = build_interview_policy_from_assessment(assessment)
        print(f"\n=== {label} ===")
        print("EmotionAssessment:")
        print(json.dumps(assessment.model_dump(), ensure_ascii=False, indent=2))
        print("InterviewPolicy:")
        print(json.dumps(policy.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
