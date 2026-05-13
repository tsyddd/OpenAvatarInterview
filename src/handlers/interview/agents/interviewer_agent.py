from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from ..interview_config import InterviewAgentConfig
from ..models.interview_models import InterviewSessionState
from ..prompts.loader import PromptLoader

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover
    END = "__end__"
    StateGraph = None


class InterviewerPayload(TypedDict, total=False):
    state: InterviewSessionState
    user_message: str
    prompt: str
    should_end: bool


class InterviewerAgent:
    def __init__(self, config: InterviewAgentConfig):
        self.config = config
        self.prompts = PromptLoader(Path(__file__).resolve().parents[1] / "prompts")
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(InterviewerPayload)
        graph.add_node("prepare_prompt", self._prepare_prompt)
        graph.add_node("decide_end", self._decide_end)
        graph.add_edge("prepare_prompt", "decide_end")
        graph.add_edge("decide_end", END)
        graph.set_entry_point("prepare_prompt")
        return graph.compile()

    def plan_turn(self, state: InterviewSessionState, user_message: str) -> InterviewerPayload:
        payload: InterviewerPayload = {
            "state": state,
            "user_message": user_message,
        }
        if self.graph is not None:
            return self.graph.invoke(payload)
        payload = self._prepare_prompt(payload)
        return self._decide_end(payload)

    def _prepare_prompt(self, payload: InterviewerPayload) -> InterviewerPayload:
        state = payload["state"]
        if not state.current_question:
            if state.question_plan:
                state.current_question = state.question_plan[min(state.current_question_index, len(state.question_plan) - 1)]
            else:
                state.current_question = self.config.opening_prompt
        recent_turns = "\n".join(
            f"{turn.role}: {turn.text}"
            for turn in state.turns[-6:]
        ) or "暂无"
        payload["prompt"] = self.prompts.render(
            "interviewer.md",
            {
                "resume_summary": state.resume_summary or state.resume_text or "暂无简历信息",
                "current_question": state.current_question,
                "recent_turns": recent_turns,
            },
        )
        return payload

    def _decide_end(self, payload: InterviewerPayload) -> InterviewerPayload:
        state = payload["state"]
        user_message = payload["user_message"].strip()
        interviewer_turns = sum(1 for turn in state.turns if turn.role == "interviewer")
        payload["should_end"] = (
            interviewer_turns >= self.config.max_questions
            or "结束面试" in user_message
            or "可以结束" in user_message
        )
        return payload
