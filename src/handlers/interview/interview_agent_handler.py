from __future__ import annotations

import re
import threading
from abc import ABC
from pathlib import Path
from typing import Dict, Optional, cast

import gradio
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
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

from .agents.dialogue_analyzer_agent import DialogueAnalyzerAgent
from .agents.evaluation_agent import EvaluationAgent
from .agents.interviewer_agent import InterviewerAgent
from .agents.question_planner_agent import QuestionPlannerAgent
from .agents.report_generator_agent import ReportGeneratorAgent
from .agents.resume_analyzer_agent import ResumeAnalyzerAgent
from .emotion.emotion_agent import EmotionAgent
from .graph.interview_graph import InterviewGraph
from .interview_config import InterviewAgentConfig
from .interview_context import InterviewHandlerContext
from .models.interview_models import InterviewSessionState
from .services.resume_parser import ResumeParser
from .services.report_pdf_renderer import ReportPdfRenderer
from .services.report_html_renderer import ReportHtmlRenderer
from .storage.session_repository import InterviewSessionRepository


class InterviewAgentHandler(HandlerBase, ABC):
    CLOSING_REPLY_PATTERNS = (
        "面试到这里",
        "今天的面试就到这里",
        "今天的交流就到这里",
        "感谢你的分享",
        "后续我们会",
        "之后会通知",
        "稍后会通知",
    )

    def __init__(self):
        super().__init__()
        self.output_definition: Optional[DataBundleDefinition] = None
        self._routes_registered = False
        self.resume_parser = ResumeParser()
        self.report_pdf_renderer = ReportPdfRenderer()
        self.report_html_renderer = ReportHtmlRenderer()
        self._handler_config: Optional[InterviewAgentConfig] = None

    def get_handler_info(self) -> HandlerBaseInfo:
        return HandlerBaseInfo(config_model=InterviewAgentConfig)

    def load(self, engine_config: ChatEngineConfigModel, handler_config: Optional[HandlerBaseConfigModel] = None):
        self.output_definition = DataBundleDefinition()
        self.output_definition.add_entry(DataBundleEntry.create_text_entry("avatar_text"))
        if isinstance(handler_config, InterviewAgentConfig):
            if not handler_config.api_key:
                raise ValueError("InterviewAgent requires api_key or DASHSCOPE_API_KEY.")
            self._handler_config = handler_config

    def create_context(self, session_context: SessionContext, handler_config: Optional[HandlerBaseConfigModel] = None):
        config = handler_config if isinstance(handler_config, InterviewAgentConfig) else InterviewAgentConfig()
        context = InterviewHandlerContext(session_context.session_info.session_id)
        context.config = config
        context.client = OpenAI(api_key=config.api_key, base_url=config.api_url, timeout=60.0)
        context.repo = InterviewSessionRepository(base_dir=Path(config.session_base_dir))
        context.state = context.repo.load_state(context.session_id) or InterviewSessionState(
            session_id=context.session_id,
            question_plan=list(config.question_bank),
            current_question=config.opening_prompt,
        )

        # Create all agents
        interviewer = InterviewerAgent(config)
        evaluator = EvaluationAgent(config, context.client)
        resume_analyzer = ResumeAnalyzerAgent(config, context.client)
        question_planner = QuestionPlannerAgent(config, context.client)
        dialogue_analyzer = DialogueAnalyzerAgent(config, context.client)
        report_generator = ReportGeneratorAgent(config, context.client)
        emotion_agent = EmotionAgent(config, None)

        context.graph = InterviewGraph(
            interviewer=interviewer,
            evaluator=evaluator,
            reporter=None,
            resume_analyzer=resume_analyzer,
            question_planner=question_planner,
            dialogue_analyzer=dialogue_analyzer,
            report_generator=report_generator,
            emotion_agent=emotion_agent,
        )
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

        handler = self  # capture for use in endpoints

        @app.get("/interview", response_class=HTMLResponse)
        async def interview_page():
            return HTMLResponse(
                "<html><body><h1>OpenAvatarInterview</h1><p>会话已启用。请使用现有 LAM/RTC 客户端进入对话。</p></body></html>"
            )

        @app.get("/openavatarinterview/sessions/{session_id}")
        async def get_session_status(session_id: str):
            repo = InterviewSessionRepository(base_dir=Path(handler._handler_config.session_base_dir if handler._handler_config else "runtime/sessions"))
            state = repo.load_state(session_id)
            if state is None:
                return JSONResponse({"session_id": session_id, "exists": False})
            return JSONResponse(
                {
                    "session_id": session_id,
                    "exists": True,
                    "stage": state.stage,
                    "report_status": state.report_status,
                    "report_error": state.report_error,
                    "resume_filename": state.resume_filename,
                    "turn_count": len(state.turns),
                    "report_ready": bool(state.final_report),
                    "report_pdf_ready": bool(state.report_pdf_filename),
                    "report_pdf_filename": state.report_pdf_filename,
                    "questions_ready": bool(state.question_plan_details),
                }
            )

        @app.post("/openavatarinterview/sessions/{session_id}/resume")
        async def upload_resume(session_id: str, file: UploadFile = File(...)):
            repo = InterviewSessionRepository(base_dir=Path(handler._handler_config.session_base_dir if handler._handler_config else "runtime/sessions"))
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in {".pdf", ".docx", ".txt", ".md"}:
                raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT, and MD resumes are supported.")
            session_dir = repo.session_dir(session_id)
            stored_path = session_dir / (file.filename or f"resume{suffix}")
            stored_path.write_bytes(await file.read())
            resume_text = handler.resume_parser.parse(stored_path)
            state = repo.load_state(session_id) or InterviewSessionState(session_id=session_id)
            state.resume_filename = stored_path.name
            state.resume_text = resume_text
            state.resume_summary = handler.resume_parser.summarize(resume_text)
            repo.save_resume_file(session_id, stored_path)
            repo.save_resume_text(session_id, state.resume_text)
            repo.save_state(session_id, state)

            # Immediately trigger resume analysis + question planning in background
            if handler._handler_config and handler._handler_config.api_key:
                threading.Thread(
                    target=handler._analyze_resume_background,
                    args=(session_id, state, handler._handler_config, repo),
                    daemon=True,
                ).start()

            return JSONResponse({"session_id": session_id, "resume_received": True, "resume_filename": state.resume_filename})

        @app.get("/openavatarinterview/sessions/{session_id}/report", response_class=PlainTextResponse)
        async def download_report(session_id: str):
            repo = InterviewSessionRepository(base_dir=Path(handler._handler_config.session_base_dir if handler._handler_config else "runtime/sessions"))
            state = repo.load_state(session_id)
            if state is None or not state.final_report:
                raise HTTPException(status_code=404, detail="Report not ready.")
            return PlainTextResponse(state.final_report.get("markdown", ""), media_type="text/markdown; charset=utf-8")

        @app.get("/openavatarinterview/sessions/{session_id}/report/html", response_class=HTMLResponse)
        async def download_report_html(session_id: str):
            repo = InterviewSessionRepository(base_dir=Path(handler._handler_config.session_base_dir if handler._handler_config else "runtime/sessions"))
            state = repo.load_state(session_id)
            if state is None:
                raise HTTPException(status_code=404, detail="Session not found.")
            html_path = repo.session_dir(session_id) / (state.report_html_filename or "report.html")
            if html_path.exists():
                return HTMLResponse(html_path.read_text(encoding="utf-8"))
            if state.final_report and state.final_report.get("markdown"):
                return HTMLResponse(handler.report_html_renderer.render(state.final_report.get("markdown", "")))
            raise HTTPException(status_code=404, detail="HTML report not ready.")

        @app.get("/openavatarinterview/sessions/{session_id}/report/pdf")
        async def download_report_pdf(session_id: str):
            repo = InterviewSessionRepository(base_dir=Path(handler._handler_config.session_base_dir if handler._handler_config else "runtime/sessions"))
            state = repo.load_state(session_id)
            if state is None or not state.report_pdf_filename:
                raise HTTPException(status_code=404, detail="PDF report not ready.")
            pdf_path = repo.session_dir(session_id) / state.report_pdf_filename
            if not pdf_path.exists():
                raise HTTPException(status_code=404, detail="PDF report not found.")
            return FileResponse(pdf_path, media_type="application/pdf", filename=state.report_pdf_filename)

        @app.get("/openavatarinterview/sessions/{session_id}/questions")
        async def get_questions(session_id: str):
            repo = InterviewSessionRepository(base_dir=Path(handler._handler_config.session_base_dir if handler._handler_config else "runtime/sessions"))
            state = repo.load_state(session_id)
            if state is None:
                raise HTTPException(status_code=404, detail="Session not found.")
            return JSONResponse({
                "session_id": session_id,
                "questions": state.question_plan_details,
                "question_texts": state.question_plan,
            })

        @app.get("/openavatarinterview/sessions/{session_id}/analysis")
        async def get_analysis(session_id: str):
            repo = InterviewSessionRepository(base_dir=Path(handler._handler_config.session_base_dir if handler._handler_config else "runtime/sessions"))
            state = repo.load_state(session_id)
            if state is None:
                raise HTTPException(status_code=404, detail="Session not found.")
            return JSONResponse({
                "session_id": session_id,
                "dialogue_analysis": state.dialogue_analysis,
                "final_evaluation": state.final_evaluation,
                "final_report": state.final_report,
                "report_status": state.report_status,
                "report_error": state.report_error,
                "report_ready": bool(state.final_report),
                "report_pdf_ready": bool(state.report_pdf_filename),
                "report_pdf_filename": state.report_pdf_filename,
                "stage": state.stage,
            })

        self._routes_registered = True

    def _analyze_resume_background(self, session_id: str, state: InterviewSessionState, config: InterviewAgentConfig, repo: InterviewSessionRepository):
        """Run resume analysis and question planning in background thread."""
        try:
            client = OpenAI(api_key=config.api_key, base_url=config.api_url, timeout=30.0)
            resume_analyzer = ResumeAnalyzerAgent(config, client)
            question_planner = QuestionPlannerAgent(config, client)

            logger.info(f"[{session_id}] Analyzing resume...")
            state.resume_analysis = resume_analyzer.analyze(state.resume_text)
            logger.info(f"[{session_id}] Resume analysis done")
            repo.save_state(session_id, state)

            logger.info(f"[{session_id}] Generating question plan...")
            questions = question_planner.plan(state.resume_analysis)
            state.question_plan_details = questions
            state.question_plan = [q["question"] for q in questions]
            logger.info(f"[{session_id}] Question plan ready: {len(questions)} questions")

            repo.save_state(session_id, state)
            client.close()
        except Exception as e:
            logger.error(f"[{session_id}] Resume analysis failed: {e}")

    def _post_interview_background(self, session_id: str, state: InterviewSessionState, graph: InterviewGraph, repo: InterviewSessionRepository):
        """Run dialogue analysis and report generation in background thread."""
        try:
            state.report_status = "pending"
            state.report_error = None
            repo.save_state(session_id, state)
            graph.run_post_interview_pipeline(state)
            state.report_status = "ready"
            state.report_error = None
            if state.final_report and state.final_report.get("markdown"):
                try:
                    html_content = self.report_html_renderer.render(state.final_report.get("markdown", ""))
                    repo.save_report_html(session_id, html_content)
                    state.report_html_filename = "report.html"
                except Exception as html_exc:
                    state.report_html_filename = None
                    logger.warning(f"[{session_id}] HTML export failed: {html_exc}")
                try:
                    pdf_bytes = self.report_pdf_renderer.render(state.final_report.get("markdown", ""))
                    repo.save_report_pdf(session_id, pdf_bytes)
                    state.report_pdf_filename = "report.pdf"
                except Exception as pdf_exc:
                    state.report_pdf_filename = None
                    state.report_error = f"PDF export failed: {pdf_exc}"
                    logger.warning(f"[{session_id}] PDF export failed: {pdf_exc}")
            repo.save_state(session_id, state)
            if state.final_evaluation:
                repo.save_evaluation(session_id, state.final_evaluation)
            if state.final_report:
                repo.save_report_markdown(session_id, state.final_report.get("markdown", ""))
                repo.save_report_json(session_id, state.final_report.get("json", {}))
            logger.info(f"[{session_id}] Post-interview pipeline complete")
        except Exception as e:
            state.report_status = "failed"
            state.report_error = str(e)
            repo.save_state(session_id, state)
            logger.error(f"[{session_id}] Post-interview pipeline failed: {e}")

    def _refine_emotion_background(
        self,
        session_id: str,
        state: InterviewSessionState,
        chat_text: str,
        config: InterviewAgentConfig,
        repo: InterviewSessionRepository,
    ) -> None:
        try:
            client = OpenAI(api_key=config.api_key, base_url=config.api_url, timeout=20.0)
            emotion_agent = EmotionAgent(config, client)
            interviewer = InterviewerAgent(config)
            evaluator = EvaluationAgent(config, client)
            graph = InterviewGraph(interviewer=interviewer, evaluator=evaluator, reporter=None, emotion_agent=emotion_agent)
            latest_state = repo.load_state(session_id) or state
            assessment = emotion_agent.assess(graph.build_emotion_input(latest_state, chat_text))
            graph.apply_emotion_assessment(latest_state, assessment, source="refined")
            repo.save_state(session_id, latest_state)
            logger.info(
                f"[{session_id}] Emotion refined: state={assessment.state.value}, "
                f"strategy={assessment.strategy.value}, confidence={assessment.confidence:.2f}"
            )
            client.close()
        except Exception as exc:
            logger.warning(f"[{session_id}] Emotion refinement failed: {type(exc).__name__}: {exc}")

    def _looks_like_closing_reply(self, reply: str) -> bool:
        normalized = re.sub(r"\s+", "", reply or "")
        return any(pattern in normalized for pattern in self.CLOSING_REPLY_PATTERNS)

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

        fast_assessment = context.graph.fast_assess_emotion(context.state, chat_text)
        if fast_assessment is not None:
            context.graph.apply_emotion_assessment(context.state, fast_assessment, source="fast")
            context.repo.save_state(context.session_id, context.state)
            logger.info(
                f"[{context.session_id}] Emotion fast-path: state={fast_assessment.state.value}, "
                f"strategy={fast_assessment.strategy.value}, confidence={fast_assessment.confidence:.2f}"
            )

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
            if context.state.stage != "completed" and self._looks_like_closing_reply(full_reply):
                context.state.stage = "completed"
            context.repo.append_transcript(context.session_id, {"role": "candidate", "text": chat_text, "event": "turn"})
            context.repo.append_transcript(context.session_id, {"role": "interviewer", "text": full_reply, "event": "turn"})
            context.repo.save_state(context.session_id, context.state)

            if context.config and context.config.api_key:
                threading.Thread(
                    target=self._refine_emotion_background,
                    args=(context.session_id, context.state, chat_text, context.config, context.repo),
                    daemon=True,
                ).start()

            # Post-interview pipeline in background (doesn't block chat response)
            should_start_post_pipeline = (
                context.state.stage == "completed"
                and context.graph is not None
                and context.state.report_status not in {"pending", "ready"}
                and not context.state.final_report
            )
            if should_start_post_pipeline and context.graph:
                context.state.report_status = "pending"
                context.state.report_error = None
                context.repo.save_state(context.session_id, context.state)
                threading.Thread(
                    target=self._post_interview_background,
                    args=(context.session_id, context.state, context.graph, context.repo),
                    daemon=True,
                ).start()
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
