from handlers.interview.models.interview_models import InterviewSessionState, InterviewTurn


def test_session_state_defaults():
    state = InterviewSessionState(session_id="s1")

    assert state.session_id == "s1"
    assert state.stage == "created"
    assert state.turns == []
    assert state.current_question == ""
    assert state.question_plan == []


def test_session_state_round_trip():
    state = InterviewSessionState(
        session_id="s2",
        current_question="介绍一下你最近做的项目。",
        turns=[InterviewTurn(role="candidate", text="我最近做了一个检索系统。")],
    )

    restored = InterviewSessionState.from_dict(state.to_dict())

    assert restored.session_id == "s2"
    assert restored.current_question == "介绍一下你最近做的项目。"
    assert len(restored.turns) == 1
    assert restored.turns[0].role == "candidate"
