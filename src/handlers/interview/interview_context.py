from __future__ import annotations

from typing import Optional, Set

from openai import OpenAI

from chat_engine.contexts.handler_context import HandlerContext
from chat_engine.data_models.chat_stream import StreamKey

from .graph.interview_graph import InterviewGraph
from .interview_config import InterviewAgentConfig
from .models.interview_models import InterviewSessionState
from .storage.session_repository import InterviewSessionRepository


class InterviewHandlerContext(HandlerContext):
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.config: Optional[InterviewAgentConfig] = None
        self.client: Optional[OpenAI] = None
        self.state = InterviewSessionState(session_id=session_id)
        self.repo: Optional[InterviewSessionRepository] = None
        self.graph: Optional[InterviewGraph] = None
        self.input_texts: str = ""
        self.output_texts: str = ""
        self.active_stream_keys: Set[StreamKey] = set()
