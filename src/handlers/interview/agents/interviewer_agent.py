from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from ..emotion.emotion_types import EmotionAssessment
from ..emotion.interview_policy import InterviewPolicy, build_interview_policy_from_assessment
from ..emotion.interviewer_integration import build_interviewer_context_with_emotion
from ..interview_config import InterviewAgentConfig
from ..models.interview_models import InterviewSessionState
from ..prompts.loader import PromptLoader

try:
    from langgraph.graph import END, StateGraph
except Exception:
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

        # Determine current question from plan
        if not state.current_question:
            if state.question_plan:
                idx = min(state.current_question_index, len(state.question_plan) - 1)
                state.current_question = state.question_plan[idx]
            else:
                state.current_question = self.config.opening_prompt

        # Build question plan context
        question_plan_text = ""
        if state.question_plan_details:
            lines = []
            for i, q in enumerate(state.question_plan_details):
                marker = "→ " if i == state.current_question_index else "  "
                status = "【当前】" if i == state.current_question_index else ("【已完成】" if i < state.current_question_index else "")
                lines.append(f"{marker}{i+1}. [{q.get('category', '')}] {q.get('question', '')} {status}")
            question_plan_text = "\n".join(lines)

        recent_turns = "\n".join(
            f"{turn.role}: {turn.text}"
            for turn in state.turns[-8:]
        ) or "暂无"
        emotion_context = self._build_emotion_context(state)

        render_vars = {
            "resume_summary": state.resume_summary or state.resume_text or "暂无简历信息",
            "current_question": state.current_question,
            "recent_turns": recent_turns,
            "emotion_context": emotion_context,
        }
        if question_plan_text:
            render_vars["question_plan"] = question_plan_text
            render_vars["current_followup_count"] = str(state.current_followup_count)
            render_vars["max_followups"] = str(self.config.max_followups_per_question)
            payload["prompt"] = self.prompts.render("interviewer_with_plan.md", render_vars)
        else:
            payload["prompt"] = self.prompts.render("interviewer.md", render_vars)

        return payload

    def _build_emotion_context(self, state: InterviewSessionState) -> str:
        raw_assessment = (
            state.latest_refined_emotion_assessment
            or state.latest_fast_emotion_assessment
            or state.latest_emotion_assessment
            or {}
        )
        raw_policy = state.latest_interview_policy or {}
        if not raw_assessment:
            return "暂无"
        try:
            assessment = EmotionAssessment.model_validate(raw_assessment)
        except Exception:
            return "暂无"
        try:
            policy = InterviewPolicy.model_validate(raw_policy) if raw_policy else build_interview_policy_from_assessment(assessment)
        except Exception:
            policy = build_interview_policy_from_assessment(assessment)
        return build_interviewer_context_with_emotion(assessment, policy)

    def _decide_end(self, payload: InterviewerPayload) -> InterviewerPayload:
        state = payload["state"]
        user_message = payload["user_message"].strip()

        # User-initiated end
        if "结束面试" in user_message or "可以结束" in user_message:
            payload["should_end"] = True
            return payload

        # Plan-based end: all questions in the plan have been fully exhausted
        if state.question_plan:
            q_count = len(state.question_plan)
            last_idx = q_count - 1
            max_followups = self.config.max_followups_per_question
            plan_exhausted = (
                state.current_question_index > last_idx
                or (
                    state.current_question_index == last_idx
                    and state.current_followup_count >= max_followups
                )
            )
            payload["should_end"] = plan_exhausted
        else:
            # Fallback: no question plan, use max_questions count
            interviewer_turns = sum(1 for turn in state.turns if turn.role == "interviewer")
            payload["should_end"] = interviewer_turns >= self.config.max_questions
        return payload
