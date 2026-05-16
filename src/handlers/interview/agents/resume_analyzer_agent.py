from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from openai import OpenAI

from ..interview_config import InterviewAgentConfig
from ..prompts.loader import PromptLoader

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = "__end__"
    StateGraph = None


class ResumeAnalysisPayload(TypedDict, total=False):
    resume_text: str
    result: dict


class ResumeAnalyzerAgent:
    def __init__(self, config: InterviewAgentConfig, client: OpenAI | None):
        self.config = config
        self.client = client
        self.prompts = PromptLoader(Path(__file__).resolve().parents[1] / "prompts")
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(ResumeAnalysisPayload)
        graph.add_node("analyze", self._analyze)
        graph.add_edge("analyze", END)
        graph.set_entry_point("analyze")
        return graph.compile()

    def analyze(self, resume_text: str) -> dict:
        payload: ResumeAnalysisPayload = {"resume_text": resume_text}
        if self.graph is not None:
            return self.graph.invoke(payload).get("result", {})
        return self._analyze(payload).get("result", {})

    @staticmethod
    def _fallback_result() -> dict:
        return {
            "basic_info": {"name": None, "education": None, "work_years": None, "current_role": None},
            "skills": [],
            "experience_summary": "无法解析简历",
            "project_highlights": [],
            "strengths": [],
            "potential_concerns": [],
        }

    @classmethod
    def _normalize_result(cls, value: object) -> dict:
        return value if isinstance(value, dict) else cls._fallback_result()

    def _analyze(self, payload: ResumeAnalysisPayload) -> ResumeAnalysisPayload:
        resume_text = payload["resume_text"]
        fallback = self._fallback_result()
        if self.client is None or not resume_text.strip():
            payload["result"] = fallback
            return payload
        try:
            response = self.client.chat.completions.create(
                model=self.config.resume_analyzer_model,
                messages=[
                    {"role": "system", "content": self.prompts.read("resume_analyzer.md")},
                    {"role": "user", "content": resume_text},
                ],
                stream=False,
                response_format={"type": "json_object"},
                max_tokens=1500,
            )
            content = response.choices[0].message.content if response and response.choices else "{}"
            payload["result"] = self._normalize_result(json.loads(content or "{}"))
        except Exception:
            payload["result"] = fallback
        return payload
