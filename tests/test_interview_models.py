from handlers.interview.models.interview_models import InterviewSessionState, InterviewTurn


def test_session_state_defaults():
    state = InterviewSessionState(session_id="s1")

    assert state.session_id == "s1"
    assert state.stage == "created"
    assert state.report_status == "idle"
    assert state.turns == []
    assert state.current_question == ""
    assert state.question_plan == []


def test_session_state_round_trip():
    state = InterviewSessionState(
        session_id="s2",
        current_question="介绍一下你最近做的项目。",
        turns=[InterviewTurn(role="candidate", text="我最近做了一个检索系统。")],
        report_status="ready",
        report_error=None,
        report_pdf_filename="report.pdf",
        report_html_filename="report.html",
        latest_fast_emotion_assessment={
            "state": "stable",
            "confidence": 0.55,
            "signals": ["回答较短"],
            "risk_level": "low",
            "strategy": "reduce_difficulty",
            "interviewer_hint": "先温和确认候选人状态。",
            "suggested_transition": "我们先从最熟悉的部分开始。",
        },
        latest_refined_emotion_assessment={
            "state": "anxious",
            "confidence": 0.82,
            "signals": ["出现不确定表达"],
            "risk_level": "medium",
            "strategy": "decompress",
            "interviewer_hint": "先缓和气氛",
            "suggested_transition": "我们先从你最熟悉的部分开始。",
        },
        latest_emotion_assessment={
            "state": "anxious",
            "confidence": 0.82,
            "signals": ["出现不确定表达"],
            "risk_level": "medium",
            "strategy": "decompress",
            "interviewer_hint": "先缓和气氛",
            "suggested_transition": "我们先从你最熟悉的部分开始。",
        },
        emotion_state_history=["stable", "anxious"],
    )

    restored = InterviewSessionState.from_dict(state.to_dict())

    assert restored.session_id == "s2"
    assert restored.current_question == "介绍一下你最近做的项目。"
    assert restored.report_status == "ready"
    assert restored.report_pdf_filename == "report.pdf"
    assert restored.report_html_filename == "report.html"
    assert len(restored.turns) == 1
    assert restored.turns[0].role == "candidate"
    assert restored.latest_fast_emotion_assessment is not None
    assert restored.latest_fast_emotion_assessment["state"] == "stable"
    assert restored.latest_refined_emotion_assessment is not None
    assert restored.latest_refined_emotion_assessment["state"] == "anxious"
    assert restored.latest_emotion_assessment is not None
    assert restored.latest_emotion_assessment["state"] == "anxious"
    assert restored.emotion_state_history == ["stable", "anxious"]
