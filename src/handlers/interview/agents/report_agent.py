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


class ReportPayload(TypedDict, total=False):
    state: InterviewSessionState
    evaluation: dict
    markdown: str
    report_json: dict


class ReportAgent:
    def __init__(self, config: InterviewAgentConfig, client: OpenAI | None):
        self.config = config
        self.client = client
        self.prompts = PromptLoader(Path(__file__).resolve().parents[1] / "prompts")
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(ReportPayload)
        graph.add_node("render_report", self._render_report)
        graph.add_edge("render_report", END)
        graph.set_entry_point("render_report")
        return graph.compile()

    def generate(self, state: InterviewSessionState, evaluation: dict) -> tuple[str, dict]:
        payload: ReportPayload = {"state": state, "evaluation": evaluation}
        if self.graph is not None:
            result = self.graph.invoke(payload)
        else:
            result = self._render_report(payload)
        return result.get("markdown", ""), result.get("report_json", {})

    def _render_report(self, payload: ReportPayload) -> ReportPayload:
        state = payload["state"]
        evaluation = payload["evaluation"]
        transcript = "\n".join(f"{turn.role}: {turn.text}" for turn in state.turns)
        fallback_markdown = (
            "# 面试报告\n\n"
            f"## 面试概览\n\n共记录 {len(state.turns)} 条对话。\n\n"
            "## 评估摘要\n\n"
            f"{json.dumps(evaluation, ensure_ascii=False, indent=2)}\n"
        )
        if self.client is None:
            payload["markdown"] = fallback_markdown
            payload["report_json"] = {"summary": evaluation, "turn_count": len(state.turns)}
            return payload
        try:
            response = self.client.chat.completions.create(
                model=self.config.report_model_name,
                messages=[
                    {"role": "system", "content": self.prompts.read("reporter.md")},
                    {
                        "role": "user",
                        "content": f"评估结果：{json.dumps(evaluation, ensure_ascii=False)}\n\n面试记录：\n{transcript}",
                    },
                ],
                stream=False,
                max_tokens=1200,
            )
            content = response.choices[0].message.content if response and response.choices else ""
            payload["markdown"] = content or fallback_markdown
            payload["report_json"] = {"summary": evaluation, "turn_count": len(state.turns)}
        except Exception:
            payload["markdown"] = fallback_markdown
            payload["report_json"] = {"summary": evaluation, "turn_count": len(state.turns)}
        return payload
