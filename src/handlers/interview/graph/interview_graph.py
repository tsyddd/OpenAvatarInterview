from __future__ import annotations

from dataclasses import replace
from typing import Any

from loguru import logger

from ..agents.dialogue_analyzer_agent import DialogueAnalyzerAgent
from ..agents.evaluation_agent import EvaluationAgent
from ..agents.interviewer_agent import InterviewerAgent
from ..agents.question_planner_agent import QuestionPlannerAgent
from ..agents.report_generator_agent import ReportGeneratorAgent
from ..agents.resume_analyzer_agent import ResumeAnalyzerAgent
from ..models.interview_models import InterviewSessionState, InterviewTurn


class InterviewGraph:
    def __init__(
        self,
        interviewer: InterviewerAgent,
        evaluator: EvaluationAgent,
        reporter: None,  # kept for backward compat, unused
        resume_analyzer: ResumeAnalyzerAgent | None = None,
        question_planner: QuestionPlannerAgent | None = None,
        dialogue_analyzer: DialogueAnalyzerAgent | None = None,
        report_generator: ReportGeneratorAgent | None = None,
    ):
        self.interviewer = interviewer
        self.evaluator = evaluator
        self.resume_analyzer = resume_analyzer
        self.question_planner = question_planner
        self.dialogue_analyzer = dialogue_analyzer
        self.report_generator = report_generator

    def plan_turn(self, state: InterviewSessionState, user_message: str) -> dict:
        return self.interviewer.plan_turn(state, user_message)

    def finalize_turn(
        self,
        state: InterviewSessionState,
        user_message: str,
        reply: str,
        should_end: bool,
    ) -> InterviewSessionState:
        next_state = replace(state)
        next_state.turns = list(state.turns)
        next_state.covered_topics = list(state.covered_topics)
        next_state.question_plan_details = list(state.question_plan_details)
        if state.resume_analysis:
            next_state.resume_analysis = dict(state.resume_analysis)

        next_state.turns.append(InterviewTurn(role="candidate", text=user_message))
        next_state.turns.append(InterviewTurn(role="interviewer", text=reply))
        next_state.stage = "active"

        # Advance question if followup limit reached
        if next_state.question_plan and next_state.current_followup_count >= self.interviewer.config.max_followups_per_question:
            next_state.current_question_index += 1
            next_state.current_followup_count = 0
            if next_state.current_question_index < len(next_state.question_plan):
                next_state.current_question = next_state.question_plan[next_state.current_question_index]
            else:
                next_state.current_question = ""
        else:
            next_state.current_followup_count += 1

        if should_end:
            next_state.stage = "completed"
            # Post-interview pipeline runs in background thread (see handler)

        return next_state

    def run_post_interview_pipeline(self, state: InterviewSessionState) -> None:
        """Run dialogue analysis and report generation. Called from background thread."""
        if self.dialogue_analyzer:
            logger.info("Analyzing dialogue...")
            state.dialogue_analysis = self.dialogue_analyzer.analyze(state)
            logger.info("Dialogue analysis complete")

        evaluation = self.evaluator.evaluate(state)
        state.final_evaluation = evaluation

        if self.report_generator:
            logger.info("Generating report...")
            report_md, report_json = self.report_generator.generate(
                state,
                resume_analysis=state.resume_analysis or {},
                question_plan=state.question_plan_details,
                dialogue_analysis=state.dialogue_analysis or {},
            )
            state.final_report = {"markdown": report_md, "json": report_json}
            logger.info("Report generation complete")
        else:
            state.final_report = {"markdown": "", "json": {"summary": evaluation}}
