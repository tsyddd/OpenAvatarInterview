import json

from handlers.interview.models.interview_models import InterviewSessionState, InterviewTurn
from handlers.interview.storage.session_repository import InterviewSessionRepository


def test_repository_saves_and_loads_state(tmp_path):
    repo = InterviewSessionRepository(base_dir=tmp_path)
    state = InterviewSessionState(
        session_id="abc",
        turns=[InterviewTurn(role="interviewer", text="你好，我们开始吧。")],
    )

    saved_path = repo.save_state("abc", state)
    loaded = repo.load_state("abc")

    assert saved_path.name == "session.json"
    assert loaded is not None
    assert loaded.session_id == "abc"
    assert loaded.turns[0].text == "你好，我们开始吧。"


def test_repository_appends_transcript_entries(tmp_path):
    repo = InterviewSessionRepository(base_dir=tmp_path)

    repo.append_transcript(
        "abc",
        {"role": "candidate", "text": "你好", "event": "turn"},
    )
    repo.append_transcript(
        "abc",
        {"role": "interviewer", "text": "你好，我们开始吧。", "event": "turn"},
    )

    transcript_path = tmp_path / "abc" / "transcript.jsonl"
    lines = transcript_path.read_text(encoding="utf-8").strip().splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["text"] == "你好"
