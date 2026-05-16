from handlers.interview.agents.question_planner_agent import QuestionPlannerAgent
from handlers.interview.agents.resume_analyzer_agent import ResumeAnalyzerAgent
from handlers.interview.interview_config import InterviewAgentConfig


class _FakeResponse:
    def __init__(self, content: str):
        message = type("Message", (), {"content": content})()
        choice = type("Choice", (), {"message": message})()
        self.choices = [choice]


class _FakeClient:
    def __init__(self, content: str):
        completions = type("Completions", (), {"create": lambda *args, **kwargs: _FakeResponse(content)})()
        chat = type("Chat", (), {"completions": completions})()
        self.chat = chat


def test_resume_analyzer_falls_back_when_model_returns_list():
    config = InterviewAgentConfig()
    agent = ResumeAnalyzerAgent(config, _FakeClient("[]"))

    result = agent.analyze("java backend resume text")

    assert isinstance(result, dict)
    assert result["experience_summary"] == "无法解析简历"
    assert result["skills"] == []


def test_question_planner_handles_non_dict_resume_analysis():
    config = InterviewAgentConfig()
    agent = QuestionPlannerAgent(config, None)

    questions = agent.plan([])

    assert isinstance(questions, list)
    assert len(questions) >= 3
