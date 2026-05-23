from handlers.interview.agents.interviewer_agent import InterviewerAgent
from handlers.interview.graph.interview_graph import InterviewGraph
from handlers.interview.interview_agent_handler import InterviewAgentHandler
from handlers.interview.interview_config import InterviewAgentConfig
from handlers.interview.models.interview_models import InterviewSessionState
from handlers.interview.storage.session_repository import InterviewSessionRepository


class _StubEvaluator:
    def evaluate(self, state):
        return {"overall": "strong"}


class _StubDialogueAnalyzer:
    def analyze(self, state):
        return {"summary": "good answers"}


class _StubReportGenerator:
    def generate(self, state, resume_analysis, question_plan, dialogue_analysis):
        return "# 面试报告\n\n候选人表现稳定。", {"summary": "stable"}


class _StubGraph:
    def run_post_interview_pipeline(self, state):
        state.dialogue_analysis = {"summary": "good answers"}
        state.final_evaluation = {"overall": "strong"}
        state.final_report = {
            "markdown": "# 面试报告\n\n候选人表现稳定。",
            "json": {"summary": "stable"},
        }


def test_finalize_turn_marks_session_completed_when_last_question_is_exhausted():
    config = InterviewAgentConfig(max_followups_per_question=2)
    graph = InterviewGraph(
        interviewer=InterviewerAgent(config),
        evaluator=_StubEvaluator(),
        reporter=None,
        dialogue_analyzer=_StubDialogueAnalyzer(),
        report_generator=_StubReportGenerator(),
    )
    state = InterviewSessionState(
        session_id="s1",
        stage="active",
        question_plan=["问题一"],
        current_question="问题一",
        current_question_index=0,
        current_followup_count=1,
    )

    next_state = graph.finalize_turn(
        state=state,
        user_message="这是我的回答。",
        reply="谢谢，我的问题结束了。",
        should_end=False,
    )

    assert next_state.stage == "completed"
    assert next_state.current_question == ""
    assert next_state.current_question_index == 1


def test_post_interview_background_marks_report_ready_and_writes_pdf(tmp_path):
    repo = InterviewSessionRepository(base_dir=tmp_path)
    handler = InterviewAgentHandler()
    state = InterviewSessionState(session_id="s2", stage="completed", report_status="pending")

    handler._post_interview_background("s2", state, _StubGraph(), repo)

    saved_state = repo.load_state("s2")
    assert saved_state is not None
    assert saved_state.report_status == "ready"
    assert saved_state.final_evaluation == {"overall": "strong"}
    assert saved_state.report_pdf_filename == "report.pdf"
    assert saved_state.report_html_filename == "report.html"
    assert (tmp_path / "s2" / "report.pdf").exists()
    assert (tmp_path / "s2" / "report.html").exists()


def test_closing_reply_is_detected_as_end_signal():
    handler = InterviewAgentHandler()

    assert handler._looks_like_closing_reply("今天的面试就到这里，感谢你的分享，后续我们会尽快通知你结果。")
    assert not handler._looks_like_closing_reply("这个项目不错。接下来我追问一下当时的技术选型。")
