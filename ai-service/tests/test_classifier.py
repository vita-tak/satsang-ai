import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import anthropic
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.checks import EM_DASH, names_listed_name
from src.agent.nodes.classify import SYSTEM, TOOL, make_classify_node
from src.agent.nodes.prompts import CRISIS_FLAG_LINE
from src.agent.safety_net import load_risk_patterns
from src.config import HAIKU_MODEL, RISK_PHRASES_DIR
from tests.data.classifier_set import CASES, QUANTUM_QUESTION
from tests.fakes import FakeAnthropic, route_message, scripted
from tests.private_names import PRIVATE_NAMES

PATTERNS = load_risk_patterns(RISK_PHRASES_DIR)


def classify(client: FakeAnthropic, messages: list, crisis_flagged: bool = False) -> dict:
    node = make_classify_node(client, PATTERNS)
    return node({"messages": messages, "crisis_flagged": crisis_flagged, "recent_directions": []})


def test_classifier_makes_one_forced_strict_haiku_call() -> None:
    client = scripted(route_message())
    classify(client, [HumanMessage("I feel stuck.")])

    (request,) = client.requests
    assert request["model"] == HAIKU_MODEL
    assert request["tool_choice"] == {"type": "tool", "name": "route_message"}
    assert request["tools"] == [TOOL]
    assert TOOL["strict"] is True
    assert request["system"] == SYSTEM


def test_classifier_asks_for_temperature_zero_so_borderline_messages_repeat() -> None:
    client = scripted(route_message())
    classify(client, [HumanMessage("My mother died two weeks ago.")])

    assert client.requests[0]["extra_body"] == {"temperature": 0}


def test_the_sdk_puts_temperature_zero_on_the_wire() -> None:
    """
    The installed SDK has no typed temperature parameter, so it travels in extra_body. A local
    fake server shows the JSON body the real SDK sends. No real API is called.
    """
    bodies: list[dict] = []
    reply = json.dumps({
        "id": "msg_wire", "type": "message", "role": "assistant", "model": HAIKU_MODEL,
        "content": [{"type": "tool_use", "id": "toolu_wire", "name": "route_message", "input": {
            "risk": "none", "register": "pointing", "language": "en", "search_query": "q"}}],
        "stop_reason": "tool_use", "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            self.wfile.write(reply)

        def log_message(self, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        client = anthropic.Anthropic(api_key="test-key", base_url=base_url)
        classify(client, [HumanMessage("My mother died two weeks ago.")])
    finally:
        server.shutdown()

    (body,) = bodies
    assert body["temperature"] == 0
    assert body["model"] == HAIKU_MODEL


def test_classifier_text_says_a_request_about_the_practice_is_never_off_topic() -> None:
    register = TOOL["input_schema"]["properties"]["register"]["description"]
    assert (
        "A request about meditation or the person's own practice, including a request for "
        "resources such as a book, a course or an app, is never off_topic."
    ) in register
    # It stays inside the off_topic part of the description
    assert register.index("never off_topic") > register.index("off_topic: only when")


def test_classifier_text_says_questions_about_consciousness_are_never_off_topic() -> None:
    register = TOOL["input_schema"]["properties"]["register"]["description"]
    assert (
        "A question about consciousness, the mind, awareness or the self, including one asked "
        "through science, is never off_topic."
    ) in register


def test_the_quantum_question_is_in_the_set_alone_and_after_four_earlier_exchanges() -> None:
    cases = [case for case in CASES if case.message == QUANTUM_QUESTION]
    contexts = {case.previous for case in cases if case.previous}

    assert any(case.previous is None for case in cases)
    assert len(contexts) >= 4
    assert all(case.never_off_topic and not case.should_flag for case in cases)


def test_classifier_weighs_risk_before_anything_else() -> None:
    assert list(TOOL["input_schema"]["properties"]) == [
        "risk",
        "register",
        "language",
        "search_query",
    ]


def test_classifier_text_names_no_one_and_has_no_em_dash() -> None:
    texts = [SYSTEM, TOOL["description"]] + [
        field["description"] for field in TOOL["input_schema"]["properties"].values()
    ]
    for text in texts:
        assert not names_listed_name(text, "", PRIVATE_NAMES)
        assert EM_DASH not in text


def test_classifier_sees_only_the_new_message_at_the_start() -> None:
    client = scripted(route_message())
    classify(client, [HumanMessage("Hello")])

    assert client.requests[0]["messages"] == [
        {"role": "user", "content": "The person's new message:\nHello"}
    ]


def test_classifier_sees_the_last_exchange_before_the_new_message() -> None:
    client = scripted(route_message())
    messages = [
        HumanMessage("Earlier"),
        AIMessage("Old reply"),
        HumanMessage("I keep losing focus."),
        AIMessage("Where is the losing felt?"),
        HumanMessage("In my chest."),
    ]
    classify(client, messages)

    assert client.requests[0]["messages"][0]["content"] == (
        "The person's previous message:\nI keep losing focus.\n\n"
        "The guide's previous reply:\nWhere is the losing felt?\n\n"
        "The person's new message:\nIn my chest."
    )


def test_classifier_is_told_when_a_crisis_was_flagged_earlier() -> None:
    client = scripted(route_message())
    classify(client, [HumanMessage("Thanks, I'm calmer now.")], crisis_flagged=True)

    content = client.requests[0]["messages"][0]["content"]
    assert content.startswith(CRISIS_FLAG_LINE + "\n\n")


def test_classifier_returns_what_the_model_decided() -> None:
    client = scripted(route_message(risk="unsure", register="explanatory", language="sv"))
    result = classify(client, [HumanMessage("Vad betyder vichara?")])

    assert result == {
        "risk": "unsure",
        "register": "explanatory",
        "language": "sv",
        "search_query": "the query",
    }


def test_keyword_net_raises_risk_the_classifier_missed() -> None:
    client = scripted(route_message(risk="none"))
    result = classify(client, [HumanMessage("Honestly I just want to die.")])

    assert result["risk"] == "crisis"


def test_keyword_net_uses_the_list_for_the_detected_language() -> None:
    client = scripted(route_message(risk="none", language="sv"))
    result = classify(client, [HumanMessage("Jag vill inte leva längre.")])

    assert result["risk"] == "crisis"


def test_keyword_net_never_lowers_risk() -> None:
    client = scripted(route_message(risk="unsure"))
    result = classify(client, [HumanMessage("Everything feels far away.")])

    assert result["risk"] == "unsure"


@pytest.mark.parametrize(("given", "expected"), [("SV", "sv"), (" en ", "en"), ("Swedish", None)])
def test_language_is_a_two_letter_code_or_unknown(given: str, expected: str | None) -> None:
    client = scripted(route_message(language=given))
    result = classify(client, [HumanMessage("Hello")])

    assert result["language"] == expected
