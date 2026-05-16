from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict

from loguru import logger
from openai import OpenAI

from ..interview_config import InterviewAgentConfig
from ..models.interview_models import InterviewSessionState
from ..prompts.loader import PromptLoader

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = "__end__"
    StateGraph = None


class DialogueAnalysisPayload(TypedDict, total=False):
    state: InterviewSessionState
    result: dict


class DialogueAnalyzerAgent:
    def __init__(self, config: InterviewAgentConfig, client: OpenAI | None):
        self.config = config
        self.client = client
        self.prompts = PromptLoader(Path(__file__).resolve().parents[1] / "prompts")
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(DialogueAnalysisPayload)
        graph.add_node("analyze", self._analyze)
        graph.add_edge("analyze", END)
        graph.set_entry_point("analyze")
        return graph.compile()

    def analyze(self, state: InterviewSessionState) -> dict:
        payload: DialogueAnalysisPayload = {"state": state}
        if self.graph is not None:
            return self.graph.invoke(payload).get("result", {})
        return self._analyze(payload).get("result", {})

    def _analyze(self, payload: DialogueAnalysisPayload) -> DialogueAnalysisPayload:
        state = payload["state"]
        transcript = "\n".join(f"{turn.role}: {turn.text}" for turn in state.turns)
        fallback = {
            "topic_coverage": [],
            "answer_quality": [],
            "technical_depth": {"score": 3, "analysis": "无法分析"},
            "communication": {"score": 3, "analysis": "无法分析"},
            "notable_moments": [],
            "overall_score": 3,
            "overall_comment": "模型分析不可用，使用默认结果。",
        }
        if self.client is None:
            payload["result"] = fallback
            return payload
        try:
            response = self.client.chat.completions.create(
                model=self.config.dialogue_analyzer_model,
                messages=[
                    {"role": "system", "content": self.prompts.read("dialogue_analyzer.md")},
                    {"role": "user", "content": f"请根据以上对话进行分析。请只返回JSON，不要包含markdown代码块。\n\n对话记录:\n{transcript}"},
                ],
                stream=False,
                response_format={"type": "json_object"},
                max_tokens=2000,
            )
            content = response.choices[0].message.content if response and response.choices else "{}"
            logger.info(f"Dialogue analysis raw response (first 300 chars): {str(content)[:300]}")
            extracted = self._extract_json(content or "{}")
            payload["result"] = json.loads(extracted)
        except json.JSONDecodeError as e:
            logger.warning(f"Dialogue analysis JSON parse error: {e}")
            payload["result"] = fallback
        except Exception as e:
            logger.warning(f"Dialogue analysis LLM call failed, using fallback: {type(e).__name__}: {e}")
            payload["result"] = fallback
        return payload

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        return text
