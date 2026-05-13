from __future__ import annotations

import json
import os
import re
from abc import ABC
from pathlib import Path
from typing import Dict, Optional, cast

import gradio
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from loguru import logger
from openai import APIStatusError, OpenAI

from chat_engine.common.handler_base import HandlerBase, HandlerBaseInfo, HandlerDataInfo, HandlerDetail
from chat_engine.contexts.handler_context import HandlerContext
from chat_engine.contexts.session_context import SessionContext
from chat_engine.data_models.chat_data.chat_data_model import ChatData
from chat_engine.data_models.chat_data_type import ChatDataType
from chat_engine.data_models.chat_engine_config_data import ChatEngineConfigModel, HandlerBaseConfigModel
from chat_engine.data_models.chat_signal import ChatSignal, SignalFilterRule
from chat_engine.data_models.chat_signal_type import ChatSignalType
from chat_engine.data_models.chat_stream_config import ChatStreamConfig
from chat_engine.data_models.runtime_data.data_bundle import DataBundle, DataBundleDefinition, DataBundleEntry

from .agents.evaluation_agent import EvaluationAgent
from .agents.interviewer_agent import InterviewerAgent
from .agents.report_agent import ReportAgent
from .graph.interview_graph import InterviewGraph
from .interview_config import InterviewAgentConfig
from .interview_context import InterviewHandlerContext
from .models.interview_models import InterviewSessionState
from .services.resume_parser import ResumeParser
from .storage.session_repository import InterviewSessionRepository


class InterviewAgentHandler(HandlerBase, ABC):
    def __init__(self):
        super().__init__()
        self.output_definition: Optional[DataBundleDefinition] = None
        self._routes_registered = False
        self.resume_parser = ResumeParser()

    def get_handler_info(self) -> HandlerBaseInfo:
        return HandlerBaseInfo(config_model=InterviewAgentConfig)

    def load(self, engine_config: ChatEngineConfigModel, handler_config: Optional[HandlerBaseConfigModel] = None):
        self.output_definition = DataBundleDefinition()
        self.output_definition.add_entry(DataBundleEntry.create_text_entry("avatar_text"))
        if isinstance(handler_config, InterviewAgentConfig):
            if not handler_config.api_key:
                raise ValueError("InterviewAgent requires api_key or DASHSCOPE_API_KEY.")

    def create_context(self, session_context: SessionContext, handler_config: Optional[HandlerBaseConfigModel] = None):
        config = handler_config if isinstance(handler_config, InterviewAgentConfig) else InterviewAgentConfig()
        context = InterviewHandlerContext(session_context.session_info.session_id)
        context.config = config
        context.client = OpenAI(api_key=config.api_key, base_url=config.api_url, timeout=5.0)
        context.repo = InterviewSessionRepository(base_dir=Path(config.session_base_dir))
        context.state = context.repo.load_state(context.session_id) or InterviewSessionState(
            session_id=context.session_id,
            question_plan=list(config.question_bank),
            current_question=config.opening_prompt,
        )
        interviewer = InterviewerAgent(config)
        evaluator = EvaluationAgent(config, context.client)
        reporter = ReportAgent(config, context.client)
        context.graph = InterviewGraph(interviewer, evaluator, reporter)
        return context

    def start_context(self, session_context: SessionContext, handler_context: HandlerContext):
        context = cast(InterviewHandlerContext, handler_context)
        if context.repo is not None:
            context.repo.save_state(context.session_id, context.state)

    def get_handler_detail(self, session_context: SessionContext, context: HandlerContext) -> HandlerDetail:
        definition = DataBundleDefinition()
        definition.add_entry(DataBundleEntry.create_text_entry("avatar_text"))
        return HandlerDetail(
            inputs={
                ChatDataType.HUMAN_TEXT: HandlerDataInfo(type=ChatDataType.HUMAN_TEXT),
            },
            outputs={
                ChatDataType.AVATAR_TEXT: HandlerDataInfo(type=ChatDataType.AVATAR_TEXT, definition=definition),
            },
            signal_filters=[SignalFilterRule(ChatSignalType.STREAM_CANCEL, None, None)],
        )

    def on_setup_app(self, app: FastAPI, ui: gradio.blocks.Block, parent_block: Optional[gradio.blocks.Block] = None):
        if self._routes_registered:
            return

        @app.get("/interview", response_class=HTMLResponse)
        async def interview_page():
            return HTMLResponse(
                "<html><body><h1>OpenAvatarInterview</h1><p>会话已启用。请使用现有 LAM/RTC 客户端进入对话。</p></body></html>"
            )

        @app.get("/openavatarinterview/sessions/{session_id}")
        async def get_session_status(session_id: str):
            repo = InterviewSessionRepository()
            state = repo.load_state(session_id)
            if state is None:
                return JSONResponse({"session_id": session_id, "exists": False})
            return JSONResponse(
                {
                    "session_id": session_id,
                    "exists": True,
                    "stage": state.stage,
                    "resume_filename": state.resume_filename,
                    "turn_count": len(state.turns),
                    "report_ready": bool(state.final_report),
                }
            )

        @app.post("/openavatarinterview/sessions/{session_id}/resume")
        async def upload_resume(session_id: str, file: UploadFile = File(...)):
            repo = InterviewSessionRepository()
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in {".pdf", ".docx", ".txt", ".md"}:
                raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT, and MD resumes are supported.")
            session_dir = repo.session_dir(session_id)
            stored_path = session_dir / (file.filename or f"resume{suffix}")
            stored_path.write_bytes(await file.read())
            resume_text = self.resume_parser.parse(stored_path)
            state = repo.load_state(session_id) or InterviewSessionState(session_id=session_id)
            state.resume_filename = stored_path.name
            state.resume_text = resume_text
            state.resume_summary = self.resume_parser.summarize(resume_text)
            repo.save_resume_file(session_id, stored_path)
            repo.save_resume_text(session_id, state.resume_text)
            repo.save_state(session_id, state)
            return JSONResponse({"session_id": session_id, "resume_received": True, "resume_filename": state.resume_filename})

        @app.get("/openavatarinterview/sessions/{session_id}/report", response_class=PlainTextResponse)
        async def download_report(session_id: str):
            repo = InterviewSessionRepository()
            state = repo.load_state(session_id)
            if state is None or not state.final_report:
                raise HTTPException(status_code=404, detail="Report not ready.")
            return PlainTextResponse(state.final_report.get("markdown", ""), media_type="text/markdown; charset=utf-8")

        self._routes_registered = True

    def handle(self, context: HandlerContext, inputs: ChatData, output_definitions: Dict[ChatDataType, HandlerDataInfo]):
        context = cast(InterviewHandlerContext, context)
        if inputs.type != ChatDataType.HUMAN_TEXT:
            return
        text = inputs.data.get_main_data()
        if text is not None:
            context.input_texts += text
        if not inputs.is_last_data:
            return
        chat_text = re.sub(r"<\\|.*?\\|>", "", context.input_texts).strip()
        context.input_texts = ""
        if not chat_text or context.client is None or context.graph is None or context.repo is None:
            return

        plan = context.graph.plan_turn(context.state, chat_text)
        prompt = plan.get("prompt", "")
        should_end = bool(plan.get("should_end", False))

        output_definition = output_definitions.get(ChatDataType.AVATAR_TEXT).definition
        streamer = context.data_submitter.get_streamer(ChatDataType.AVATAR_TEXT)
        stream_key = streamer.current_stream.identity.stream_key_str if streamer.current_stream is not None else None
        if stream_key is None:
            stream = streamer.new_stream(sources=[inputs.stream_id], name="interview_agent", config=ChatStreamConfig(cancelable=True))
            stream_key = stream.stream_key_str
        if stream_key:
            context.active_stream_keys.add(stream_key)

        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": chat_text}]
        full_reply = ""
        cancelled = False
        try:
            completion = context.client.chat.completions.create(
                model=context.config.model_name,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in completion:
                if stream_key and stream_key not in context.active_stream_keys:
                    cancelled = True
                    try:
                        completion.close()
                    except Exception:
                        pass
                    break
                if chunk and chunk.choices and chunk.choices[0] and chunk.choices[0].delta.content:
                    output_text = chunk.choices[0].delta.content
                    full_reply += output_text
                    output = DataBundle(output_definition)
                    output.set_main_data(output_text)
                    streamer.stream_data(output)
        except Exception as exc:
            logger.error(exc)
            if isinstance(exc, APIStatusError) and isinstance(exc.body, dict) and "message" in exc.body:
                full_reply = str(exc.body["message"])
            else:
                full_reply = f"连接错误: {exc}"
            output = DataBundle(output_definition)
            output.set_main_data(full_reply)
            streamer.stream_data(output)

        if stream_key:
            context.active_stream_keys.discard(stream_key)
        if not cancelled:
            context.state = context.graph.finalize_turn(context.state, chat_text, full_reply, should_end)
            context.repo.append_transcript(context.session_id, {"role": "candidate", "text": chat_text, "event": "turn"})
            context.repo.append_transcript(context.session_id, {"role": "interviewer", "text": full_reply, "event": "turn"})
            context.repo.save_state(context.session_id, context.state)
            if context.state.final_evaluation:
                context.repo.save_evaluation(context.session_id, context.state.final_evaluation)
            if context.state.final_report:
                context.repo.save_report_markdown(context.session_id, context.state.final_report.get("markdown", ""))
                context.repo.save_report_json(context.session_id, context.state.final_report.get("json", {}))
        end_output = DataBundle(output_definition)
        end_output.set_main_data("")
        streamer.stream_data(end_output, finish_stream=True)

    def on_signal(self, context: HandlerContext, signal: ChatSignal):
        context = cast(InterviewHandlerContext, context)
        if signal.type == ChatSignalType.STREAM_CANCEL and signal.related_stream:
            stream_key = signal.related_stream.stream_key_str
            if stream_key is not None and stream_key in context.active_stream_keys:
                context.active_stream_keys.discard(stream_key)

    def destroy_context(self, context: HandlerContext):
        context = cast(InterviewHandlerContext, context)
        if context.repo is not None:
            context.repo.save_state(context.session_id, context.state)
        if context.client is not None:
            try:
                context.client.close()
            except Exception:
                pass
            context.client = None


__all__ = ["InterviewAgentHandler"]
