from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict

from loguru import logger
from openai import OpenAI

from ..interview_config import InterviewAgentConfig
from ..prompts.loader import PromptLoader
from ..tools.web_search import search

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = "__end__"
    StateGraph = None


class QuestionPlanPayload(TypedDict, total=False):
    resume_analysis: dict
    search_results: str
    questions: list[dict]


class QuestionPlannerAgent:
    def __init__(self, config: InterviewAgentConfig, client: OpenAI | None):
        self.config = config
        self.client = client
        self.prompts = PromptLoader(Path(__file__).resolve().parents[1] / "prompts")
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        graph = StateGraph(QuestionPlanPayload)
        graph.add_node("search", self._search)
        graph.add_node("plan", self._plan)
        graph.add_edge("search", "plan")
        graph.add_edge("plan", END)
        graph.set_entry_point("search")
        return graph.compile()

    def plan(self, resume_analysis: dict) -> list[dict]:
        payload: QuestionPlanPayload = {"resume_analysis": self._normalize_resume_analysis(resume_analysis)}
        if self.graph is not None:
            result = self.graph.invoke(payload)
        else:
            payload = self._search(payload)
            result = self._plan(payload)
        return result.get("questions", [])

    @staticmethod
    def _normalize_resume_analysis(resume_analysis: object) -> dict:
        if isinstance(resume_analysis, dict):
            return resume_analysis
        return {
            "basic_info": {},
            "skills": [],
            "experience_summary": "",
            "project_highlights": [],
            "strengths": [],
            "potential_concerns": [],
        }

    def _search(self, payload: QuestionPlanPayload) -> QuestionPlanPayload:
        resume_analysis = self._normalize_resume_analysis(payload["resume_analysis"])
        skills = resume_analysis.get("skills", [])
        role = resume_analysis.get("basic_info", {}).get("current_role", "")

        queries = []
        if skills:
            queries.append(f"{' '.join(skills[:3])} 面试问题 技术考察")
        if role:
            queries.append(f"{role} 面试常见问题 深度")
        if not queries:
            queries.append("技术面试 高质量问题")

        all_results: list[str] = []
        for q in queries[:2]:
            results = search(
                q,
                num_results=3,
                provider=self.config.search_provider,
                api_key=self.config.search_api_key,
            )
            for r in results:
                all_results.append(f"- {r['title']}: {r['snippet'][:100]}")

        payload["search_results"] = "\n".join(all_results) if all_results else "暂无搜索结果"
        return payload

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from text that may be wrapped in markdown code blocks."""
        text = text.strip()
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        return text

    def _plan(self, payload: QuestionPlanPayload) -> QuestionPlanPayload:
        resume_analysis = payload["resume_analysis"]
        search_results = payload.get("search_results", "暂无搜索结果")

        fallback_questions = [
            {"question": "请介绍一下你最近的项目，你在其中担任什么角色？", "category": "项目经验", "target_skill": "项目理解", "follow_up_hints": ["遇到的最大挑战是什么？", "如何做技术选型的？"]},
            {"question": "请描述一个你解决过的有挑战性的技术问题。", "category": "问题解决", "target_skill": "问题分析", "follow_up_hints": ["排查过程是怎样的？", "最终方案的权衡考虑？"]},
            {"question": "你如何看待代码质量？在项目中如何保证？", "category": "技术深度", "target_skill": "工程素养", "follow_up_hints": ["举一个具体的例子？", "如何平衡开发速度和质量？"]},
        ]

        if self.client is None:
            payload["questions"] = fallback_questions
            return payload

        try:
            prompt = self.prompts.render(
                "question_planner.md",
                {
                    "resume_analysis": json.dumps(resume_analysis, ensure_ascii=False),
                    "search_results": search_results,
                },
            )
            response = self.client.chat.completions.create(
                model=self.config.question_planner_model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "请根据以上信息生成面试问题。请只返回JSON，不要包含markdown代码块。"},
                ],
                stream=False,
                response_format={"type": "json_object"},
                max_tokens=3000,
            )
            content = response.choices[0].message.content if response and response.choices else "{}"
            logger.info(f"Question planner raw response (first 300 chars): {str(content)[:300]}")
            extracted = self._extract_json(content or "{}")
            parsed = json.loads(extracted)
            questions = parsed.get("questions", fallback_questions)
            if not isinstance(questions, list) or len(questions) < 3:
                logger.warning(f"Question planner returned insufficient questions: {len(questions) if isinstance(questions, list) else 'not a list'}, using fallback")
                questions = fallback_questions
            logger.info(f"Question planner generated {len(questions)} questions")
            payload["questions"] = questions
        except json.JSONDecodeError as e:
            logger.warning(f"Question planner JSON parse error: {e}, content: {str(content)[:500] if content else 'empty'}")
            payload["questions"] = fallback_questions
        except Exception as e:
            logger.warning(f"Question planner LLM call failed, using fallback: {type(e).__name__}: {e}")
            payload["questions"] = fallback_questions
        return payload
