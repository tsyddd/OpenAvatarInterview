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
from ..emotion.emotion_agent import EmotionAgent
from ..emotion.emotion_types import DialogueTurn, EmotionAssessment, EmotionAssessmentInput
from ..emotion.interview_policy import build_interview_policy_from_assessment
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
        emotion_agent: EmotionAgent | None = None,
    ):
        self.interviewer = interviewer
        self.evaluator = evaluator
        self.resume_analyzer = resume_analyzer
        self.question_planner = question_planner
        self.dialogue_analyzer = dialogue_analyzer
        self.report_generator = report_generator
        self.emotion_agent = emotion_agent

    def plan_turn(self, state: InterviewSessionState, user_message: str) -> dict:
        return self.interviewer.plan_turn(state, user_message)

    def build_emotion_input(
        self,
        state: InterviewSessionState,
        user_message: str,
    ) -> EmotionAssessmentInput:
        source_turns = state.turns[-4:]
        if source_turns and source_turns[-1].role == "interviewer":
            source_turns = source_turns[:-1]
        recent_turns = [
            DialogueTurn(role=turn.role, text=turn.text)
            for turn in source_turns
        ]
        if not recent_turns or recent_turns[-1].role != "candidate" or recent_turns[-1].text != user_message:
            recent_turns.append(DialogueTurn(role="candidate", text=user_message))
        return EmotionAssessmentInput(
            current_question=state.current_question,
            candidate_answer=user_message,
            recent_history=recent_turns,
            candidate_profile_summary=state.resume_summary or state.resume_text or None,
            previous_states=list(state.emotion_state_history[-3:]),
        )

    def fast_assess_emotion(
        self,
        state: InterviewSessionState,
        user_message: str,
    ) -> EmotionAssessment | None:
        if self.emotion_agent is None:
            return None
        return self.emotion_agent.assess_rules_only(self.build_emotion_input(state, user_message))

    def apply_emotion_assessment(
        self,
        state: InterviewSessionState,
        assessment: EmotionAssessment | None,
        source: str = "effective",
    ) -> InterviewSessionState:
        if assessment is None:
            return state
        serialized = assessment.model_dump(mode="json")
        if source == "fast":
            state.latest_fast_emotion_assessment = serialized
        elif source == "refined":
            state.latest_refined_emotion_assessment = serialized

        effective = state.latest_refined_emotion_assessment or serialized
        state.latest_emotion_assessment = effective
        state.latest_interview_policy = build_interview_policy_from_assessment(
            EmotionAssessment.model_validate(effective)
        ).model_dump()
        state.emotion_state_history = [*state.emotion_state_history[-4:], assessment.state.value]
        return state

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

        # Advance question once this answer has consumed the current follow-up budget.
        if next_state.question_plan:
            next_state.current_followup_count += 1
            if next_state.current_followup_count >= self.interviewer.config.max_followups_per_question:
                next_state.current_question_index += 1
                next_state.current_followup_count = 0
                if next_state.current_question_index < len(next_state.question_plan):
                    next_state.current_question = next_state.question_plan[next_state.current_question_index]
                else:
                    next_state.current_question = ""
        else:
            next_state.current_followup_count += 1

        if should_end or self._is_plan_exhausted(next_state):
            next_state.stage = "completed"
            # Post-interview pipeline runs in background thread (see handler)

        return next_state

    def _is_plan_exhausted(self, state: InterviewSessionState) -> bool:
        if state.question_plan:
            return state.current_question_index >= len(state.question_plan) or not state.current_question
        interviewer_turns = sum(1 for turn in state.turns if turn.role == "interviewer")
        return interviewer_turns >= self.interviewer.config.max_questions

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
