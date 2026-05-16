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


class ReportGenPayload(TypedDict, total=False):
    state: InterviewSessionState
    resume_analysis: dict
    question_plan: list[dict]
    dialogue_analysis: dict
    markdown: str
    report_json: dict


class ReportGeneratorAgent:
    def __init__(self, config: InterviewAgentConfig, client: OpenAI | None):
        self.config = config
        self.client = client
        self.prompts = PromptLoader(Path(__file__).resolve().parents[1] / "prompts")
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(ReportGenPayload)
        graph.add_node("generate", self._generate)
        graph.add_edge("generate", END)
        graph.set_entry_point("generate")
        return graph.compile()

    def generate(
        self,
        state: InterviewSessionState,
        resume_analysis: dict,
        question_plan: list[dict],
        dialogue_analysis: dict,
    ) -> tuple[str, dict]:
        payload: ReportGenPayload = {
            "state": state,
            "resume_analysis": resume_analysis,
            "question_plan": question_plan,
            "dialogue_analysis": dialogue_analysis,
        }
        if self.graph is not None:
            result = self.graph.invoke(payload)
        else:
            result = self._generate(payload)
        return result.get("markdown", ""), result.get("report_json", {})

    def _generate(self, payload: ReportGenPayload) -> ReportGenPayload:
        state = payload["state"]
        resume_analysis = payload.get("resume_analysis", {})
        question_plan = payload.get("question_plan", [])
        dialogue_analysis = payload.get("dialogue_analysis", {})
        transcript = "\n".join(f"{turn.role}: {turn.text}" for turn in state.turns)

        fallback_markdown = (
            "# 面试报告\n\n"
            f"## 面试概览\n\n共记录 {len(state.turns)} 条对话。\n\n"
            "## 评估摘要\n\n"
            f"{json.dumps(dialogue_analysis, ensure_ascii=False, indent=2)}\n"
        )

        if self.client is None:
            payload["markdown"] = fallback_markdown
            payload["report_json"] = {"dialogue_analysis": dialogue_analysis, "turn_count": len(state.turns)}
            return payload

        try:
            prompt = self.prompts.render(
                "report_generator.md",
                {
                    "resume_analysis": json.dumps(resume_analysis, ensure_ascii=False),
                    "question_plan": json.dumps(question_plan, ensure_ascii=False),
                    "dialogue_analysis": json.dumps(dialogue_analysis, ensure_ascii=False),
                    "transcript": transcript,
                },
            )
            response = self.client.chat.completions.create(
                model=self.config.report_model_name,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "请根据以上信息生成面试报告，使用Markdown格式输出。"},
                ],
                stream=False,
                max_tokens=3000,
            )
            content = response.choices[0].message.content if response and response.choices else ""
            logger.info(f"Report generated, length: {len(content or '')}")
            payload["markdown"] = content or fallback_markdown
            payload["report_json"] = {
                "resume_analysis": resume_analysis,
                "question_plan": question_plan,
                "dialogue_analysis": dialogue_analysis,
                "turn_count": len(state.turns),
            }
        except Exception as e:
            logger.warning(f"Report generation LLM call failed, using fallback: {type(e).__name__}: {e}")
            payload["markdown"] = fallback_markdown
            payload["report_json"] = {"dialogue_analysis": dialogue_analysis, "turn_count": len(state.turns)}
        return payload
