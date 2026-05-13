from __future__ import annotations

from dataclasses import replace

from ..agents.evaluation_agent import EvaluationAgent
from ..agents.interviewer_agent import InterviewerAgent
from ..agents.report_agent import ReportAgent
from ..models.interview_models import InterviewSessionState, InterviewTurn


class InterviewGraph:
    def __init__(self, interviewer: InterviewerAgent, evaluator: EvaluationAgent, reporter: ReportAgent):
        self.interviewer = interviewer
        self.evaluator = evaluator
        self.reporter = reporter

    def plan_turn(self, state: InterviewSessionState, user_message: str) -> dict:
        return self.interviewer.plan_turn(state, user_message)

    def finalize_turn(self, state: InterviewSessionState, user_message: str, reply: str, should_end: bool) -> InterviewSessionState:
        next_state = replace(state)
        next_state.turns = list(state.turns)
        next_state.covered_topics = list(state.covered_topics)
        next_state.turns.append(InterviewTurn(role="candidate", text=user_message))
        next_state.turns.append(InterviewTurn(role="interviewer", text=reply))
        next_state.stage = "active"
        if should_end:
            next_state.stage = "completed"
            evaluation = self.evaluator.evaluate(next_state)
            report_md, report_json = self.reporter.generate(next_state, evaluation)
            next_state.final_evaluation = evaluation
            next_state.final_report = {
                "markdown": report_md,
                "json": report_json,
            }
        return next_state
