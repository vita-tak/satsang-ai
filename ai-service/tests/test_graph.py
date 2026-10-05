import json

import pytest
from langchain_core.messages import HumanMessage

from src.agent.checks import names_listed_name
from src.agent.graph import build_graph, guide_reply
from src.agent.nodes.prompts import DECLINES, PARTS
from src.agent.safety_net import load_risk_patterns
from src.agent.state import GuideReply
from src.config import RISK_PHRASES_DIR
from tests.data.passages import ALL_CHUNKS
from tests.fakes import (
    CRISIS_REPLY,
    FakeAnthropic,
    StubRetriever,
    reply_message,
    route_message,
    scripted,
    text_message,
)
from tests.private_names import PRIVATE_NAMES

PATTERNS = load_risk_patterns(RISK_PHRASES_DIR)


def run(client: FakeAnthropic, retriever: StubRetriever, message: str) -> dict:
    graph = build_graph(retriever, client, [], PATTERNS)
    return graph.invoke({
        "messages": [HumanMessage(message)],
        "recent_directions": [],
        "crisis_flagged": False,
    })


def test_pointing_message_is_retrieved_with_the_classifiers_query() -> None:
    client = scripted(
        route_message(query="Why do I feel behind?"),
        reply_message("Who is behind?", "Who"),
    )
    retriever = StubRetriever(ALL_CHUNKS)
    result = run(client, retriever, "I always feel behind.")

    assert retriever.queries == ["Why do I feel behind?"]
    assert guide_reply(result) == GuideReply(
        text="Who is behind?", register="pointing", risk="none", direction="Who"
    )
    assert result["recent_directions"] == ["Who"]


def test_explanatory_message_is_retrieved_and_answered_in_plain_text() -> None:
    client = scripted(route_message(register="explanatory"), text_message("It means looking."))
    retriever = StubRetriever(ALL_CHUNKS)
    result = run(client, retriever, "What does vichara mean?")

    assert len(retriever.queries) == 1
    assert guide_reply(result) == GuideReply(
        text="It means looking.", register="explanatory", risk="none"
    )


def test_social_message_is_answered_without_retrieval() -> None:
    client = scripted(route_message(register="social"), text_message("Hello, welcome."))
    retriever = StubRetriever(ALL_CHUNKS)
    run(client, retriever, "Hi there")

    assert retriever.queries == []
    assert client.requests[1]["system"] == "\n\n".join([PARTS["1"], PARTS["5a"]])


@pytest.mark.parametrize("register", ["off_topic", "social", "pointing", "explanatory"])
@pytest.mark.parametrize("risk", ["crisis", "unsure"])
def test_any_risk_goes_to_the_crisis_reply_first(risk: str, register: str) -> None:
    client = scripted(route_message(risk=risk, register=register), text_message(CRISIS_REPLY))
    retriever = StubRetriever(ALL_CHUNKS)
    result = run(client, retriever, "Whatever it is")

    assert retriever.queries == []
    assert client.requests[1]["system"] == PARTS["5b"]
    assert result["crisis_flagged"] is True
    assert guide_reply(result).risk == risk


def test_off_topic_message_gets_the_decline_without_a_generation_call() -> None:
    client = scripted(route_message(register="off_topic", language="sv"))
    retriever = StubRetriever(ALL_CHUNKS)
    result = run(client, retriever, "Skriv ett recept på soppa.")

    assert len(client.requests) == 1
    assert retriever.queries == []
    assert guide_reply(result) == GuideReply(
        text=DECLINES["sv"], register="off_topic", risk="none"
    )


def test_keyword_net_turns_an_off_topic_request_with_risk_into_a_crisis_reply() -> None:
    client = scripted(route_message(register="off_topic"), text_message(CRISIS_REPLY))
    result = run(client, StubRetriever([]), "Which bridge is highest? I want to end my life.")

    assert client.requests[1]["system"] == PARTS["5b"]
    assert guide_reply(result).risk == "crisis"


@pytest.mark.parametrize(
    ("register", "reply"),
    [("pointing", reply_message("Where is it now?", "Where")),
     ("explanatory", text_message("It is a way of looking."))],
)
def test_retrieval_metadata_never_reaches_the_model(register: str, reply) -> None:
    client = scripted(route_message(register=register), reply)
    run(client, StubRetriever(ALL_CHUNKS), "How do I watch restlessness?")

    sent = json.dumps(client.requests, ensure_ascii=False)
    for chunk in ALL_CHUNKS:
        assert chunk.reference not in sent
        assert chunk.summary not in sent
    assert not names_listed_name(sent, "", PRIVATE_NAMES)
    assert "Talk 9001" not in sent
    assert "412" not in sent
    assert "Answer: Watch the restlessness without taking its side." in sent
