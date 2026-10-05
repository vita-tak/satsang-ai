import json
from collections.abc import Callable, Iterator
from dataclasses import fields
from typing import Any

import pytest
from anthropic.types import Message
from fastapi.testclient import TestClient

from src.agent.graph import build_graph
from src.agent.nodes.prompts import CRISIS_FLAG_LINE
from src.agent.safety_net import load_risk_patterns
from src.api import main
from src.api.middleware.rate_limit import limiter
from src.audio.tts.script import AudioChunk
from src.config import RISK_PHRASES_DIR
from tests.fakes import (
    CRISIS_REPLY,
    FakeAnthropic,
    StubRetriever,
    reply_message,
    route_message,
    scripted,
    text_message,
)

PATTERNS = load_risk_patterns(RISK_PHRASES_DIR)


class FakeSpeechGraph:
    """Stands in for the speech graph: keeps what it was asked to speak and yields one chunk."""

    def __init__(self) -> None:
        self.inputs: list[dict[str, Any]] = []

    def stream(self, state: dict[str, Any], stream_mode: str) -> Iterator[AudioChunk]:
        self.inputs.append(state)
        yield AudioChunk(data="AAAA")


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., FakeAnthropic]]:
    """
    Wires a guide graph with a scripted client into the app, without running lifespan (which
    would build the real retriever and clients). Returns a function that takes the scripted
    responses and gives back the client, so a test can read what was sent.
    """
    def connect(*responses: Message) -> FakeAnthropic:
        client = scripted(*responses)
        monkeypatch.setattr(main, "graph", build_graph(StubRetriever([]), client, [], PATTERNS))
        return client

    main.sessions.clear()
    limiter.reset()
    yield connect
    main.sessions.clear()


http = TestClient(main.app)


def post(message: str, session_id: str | None = None, **extra: Any) -> dict[str, Any]:
    response = http.post("/chat", json={"message": message, "session_id": session_id, **extra})
    assert response.status_code == 200
    return response.json()


def test_chat_returns_the_reply_and_a_session_id(api: Callable[..., FakeAnthropic]) -> None:
    api(route_message(), reply_message("Where is it now?", "Where"))
    body = post("I feel tense.")

    assert body["response"] == "Where is it now?"
    assert body["session_id"] in main.sessions


def test_the_old_mode_field_is_accepted_and_ignored(api: Callable[..., FakeAnthropic]) -> None:
    api(route_message(register="social"), text_message("Hello."))
    assert post("Hi", mode="ramana")["response"] == "Hello."


def test_an_empty_message_is_refused_before_any_call(api: Callable[..., FakeAnthropic]) -> None:
    client = api()
    response = http.post("/chat", json={"message": "   "})

    assert response.status_code == 400
    assert client.requests == []


def test_a_failure_gives_a_fixed_message_and_leaks_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(params: dict[str, Any]) -> Message:
        raise RuntimeError("sk-secret /home/user/prompt.txt the person's words")

    graph = build_graph(StubRetriever([]), FakeAnthropic(fail), [], PATTERNS)
    monkeypatch.setattr(main, "graph", graph)
    limiter.reset()
    response = http.post("/chat", json={"message": "Hello"})

    assert response.status_code == 500
    assert response.json() == {"detail": "The guide could not answer. Please try again."}


def test_the_session_carries_the_recent_directions(api: Callable[..., FakeAnthropic]) -> None:
    client = api(
        route_message(),
        reply_message("Where is it now?", "Where"),
        route_message(),
        reply_message("What happens if you leave it alone?", "Leave alone"),
    )
    session_id = post("I feel tense.")["session_id"]
    post("It is in my shoulders.", session_id)

    assert "Directions used in the last two replies: Where." in (
        client.requests[3]["messages"][-1]["content"]
    )
    assert main.sessions[session_id].recent_directions == ["Where", "Leave alone"]


def test_a_flagged_crisis_stays_with_the_session_and_reaches_every_call(
    api: Callable[..., FakeAnthropic],
) -> None:
    client = api(
        route_message(risk="crisis"),
        text_message(CRISIS_REPLY),
        route_message(register="social"),
        text_message("You're welcome."),
        route_message(),
        reply_message("Take your time.", "none"),
    )
    session_id = post("I don't see a way out.")["session_id"]
    post("Thank you.", session_id)
    post("Can we talk about my practice?", session_id)

    for request in client.requests[2:]:
        assert CRISIS_FLAG_LINE in request["messages"][-1]["content"]
    assert main.sessions[session_id].crisis_flagged is True


def test_a_new_session_starts_without_the_flag(api: Callable[..., FakeAnthropic]) -> None:
    client = api(
        route_message(risk="crisis"),
        text_message(CRISIS_REPLY),
        route_message(register="social"),
        text_message("Hello."),
    )
    post("I don't see a way out.")
    new_session_id = post("Hi")["session_id"]

    assert CRISIS_FLAG_LINE not in client.requests[2]["messages"][-1]["content"]
    assert CRISIS_FLAG_LINE not in client.requests[3]["messages"][-1]["content"]
    assert main.sessions[new_session_id].crisis_flagged is False


def test_the_session_keeps_the_flag_as_a_boolean_only() -> None:
    assert [field.name for field in fields(main.Session)] == [
        "messages",
        "recent_directions",
        "crisis_flagged",
    ]


@pytest.mark.parametrize(
    ("responses", "intent"),
    [
        ([route_message(), reply_message("Where is it?", "Where")], "practice"),
        ([route_message(register="explanatory"), text_message("It means looking.")], "teaching"),
        ([route_message(register="social"), text_message("Hello.")], "social"),
        ([route_message(register="off_topic")], "off_topic"),
        ([route_message(risk="unsure"), text_message(CRISIS_REPLY)], "crisis"),
    ],
)
def test_spoken_answers_reach_the_speech_graph_through_the_adapter(
    api: Callable[..., FakeAnthropic],
    monkeypatch: pytest.MonkeyPatch,
    responses: list[Message],
    intent: str,
) -> None:
    api(*responses)
    speech = FakeSpeechGraph()
    monkeypatch.setattr(main.app.state, "speech_graph", speech, raising=False)
    response = http.post("/chat/spoken", json={"message": "Something"})

    lines = [json.loads(line) for line in response.text.splitlines()]
    assert [line["type"] for line in lines] == ["text", "audio", "done"]
    (spoken,) = speech.inputs
    assert spoken["intent"] == intent
    assert spoken["mode"] == "satsang"
    assert spoken["messages"][0].content == lines[0]["response"]
