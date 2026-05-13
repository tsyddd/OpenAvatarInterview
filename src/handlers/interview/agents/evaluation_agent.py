from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from openai import OpenAI

from ..interview_config import InterviewAgentConfig
from ..models.interview_models import InterviewSessionState
from ..prompts.loader import PromptLoader

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover
    END = "__end__"
    StateGraph = None


class EvaluationPayload(TypedDict, total=False):
    state: InterviewSessionState
    result: dict


class EvaluationAgent:
    def __init__(self, config: InterviewAgentConfig, client: OpenAI | None):
        self.config = config
        self.client = client
        self.prompts = PromptLoader(Path(__file__).resolve().parents[1] / "prompts")
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(EvaluationPayload)
        graph.add_node("evaluate", self._evaluate)
        graph.add_edge("evaluate", END)
        graph.set_entry_point("evaluate")
        return graph.compile()

    def evaluate(self, state: InterviewSessionState) -> dict:
        payload: EvaluationPayload = {"state": state}
        if self.graph is not None:
            return self.graph.invoke(payload).get("result", {})
        return self._evaluate(payload).get("result", {})

    def _evaluate(self, payload: EvaluationPayload) -> EvaluationPayload:
        state = payload["state"]
        transcript = "\n".join(f"{turn.role}: {turn.text}" for turn in state.turns)
        fallback = {
            "recommendation": "待定",
            "strengths": [],
            "risks": [],
            "topic_coverage": state.covered_topics,
            "communication": "待评估",
            "overall_summary": "模型评估不可用，使用默认结果。",
        }
        if self.client is None:
            payload["result"] = fallback
            return payload
        try:
            response = self.client.chat.completions.create(
                model=self.config.evaluator_model_name,
                messages=[
                    {"role": "system", "content": self.prompts.read("evaluator.md")},
                    {"role": "user", "content": transcript},
                ],
                stream=False,
                response_format={"type": "json_object"},
                max_tokens=600,
            )
            content = response.choices[0].message.content if response and response.choices else "{}"
            payload["result"] = json.loads(content or "{}")
        except Exception:
            payload["result"] = fallback
        return payload
