from __future__ import annotations

import os
from typing import List, Optional

from pydantic import BaseModel, Field

from chat_engine.data_models.chat_engine_config_data import HandlerBaseConfigModel


class InterviewAgentConfig(HandlerBaseConfigModel, BaseModel):
    model_name: str = Field(default="qwen-plus")
    evaluator_model_name: str = Field(default="qwen-plus")
    report_model_name: str = Field(default="qwen-plus")
    resume_analyzer_model: str = Field(default="qwen-plus")
    question_planner_model: str = Field(default="qwen-plus")
    dialogue_analyzer_model: str = Field(default="qwen-plus")
    api_key: Optional[str] = Field(default=os.getenv("DASHSCOPE_API_KEY"))
    api_url: Optional[str] = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    frontend_redirect_target: str = Field(default="/")
    session_base_dir: str = Field(default="runtime/sessions")
    max_questions: int = Field(default=10)
    max_followups_per_question: int = Field(default=2)
    opening_prompt: str = Field(default="我们开始吧。请先做一个简短的自我介绍。")
    search_provider: str = Field(default="duckduckgo")
    search_api_key: Optional[str] = Field(default=None)
    question_bank: List[str] = Field(
        default_factory=lambda: [
            "请介绍一个你最近主导或深度参与的项目，重点说明你的职责和结果。",
            "请讲一个你亲自处理过的线上问题，包括定位、处理和复盘。",
            "请讲一次你做技术方案权衡的经历，当时为什么那样选择。",
        ]
    )
