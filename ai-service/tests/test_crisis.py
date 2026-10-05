import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.crisis_lines import CrisisLine, lines_for_language, load_crisis_lines
from src.agent.nodes.generate import decline_node, make_generate_node
from src.agent.nodes.prompts import DECLINES, PARTS
from src.config import CRISIS_LINES_PATH
from tests.fakes import CRISIS_REPLY, guide_state, scripted, text_message

# Invented entries: the shipped list is empty until the owner adds verified numbers.
SWEDISH_LINE = CrisisLine(country="Sweden", languages=["sv"], name="Example line", number="11 22")
ENGLISH_LINE = CrisisLine(
    country="Ireland",
    languages=["en", "ga"],
    name="Example service",
    number="33 44",
    note="every day",
)


def crisis_request(language: str | None, lines: list[CrisisLine]) -> dict:
    client = scripted(text_message(CRISIS_REPLY))
    state = guide_state("I can't go on.", risk="crisis", language=language)
    make_generate_node(client, lines)(state)
    return client.requests[0]


def test_the_shipped_list_is_empty_until_the_owner_fills_it() -> None:
    assert load_crisis_lines(CRISIS_LINES_PATH) == []


def test_a_misspelt_key_fails_at_load(tmp_path: Path) -> None:
    path = tmp_path / "crisis_lines.json"
    entry = {"country": "Sweden", "languages": ["sv"], "name": "Example", "nubmer": "11 22"}
    path.write_text(json.dumps([entry]))

    with pytest.raises(ValidationError):
        load_crisis_lines(path)


def test_lines_follow_the_language_of_the_message() -> None:
    lines = [SWEDISH_LINE, ENGLISH_LINE]
    assert lines_for_language(lines, "sv") == [SWEDISH_LINE]
    assert lines_for_language(lines, "en") == [ENGLISH_LINE]
    assert lines_for_language(lines, None) == []


def test_crisis_call_names_only_the_lines_for_the_language() -> None:
    content = crisis_request("en", [SWEDISH_LINE, ENGLISH_LINE])["messages"][-1]["content"]

    assert content.endswith(
        "Verified crisis lines for this language:\nIreland: Example service, 33 44 (every day)"
    )
    assert "Sweden" not in content


def test_crisis_call_says_there_is_no_number_when_the_list_has_none() -> None:
    content = crisis_request("sv", [ENGLISH_LINE])["messages"][-1]["content"]
    assert content.endswith(
        "Verified crisis lines for this language: none. Name no phone number. Follow step 3 for "
        "when no number is provided."
    )


def test_crisis_reply_sets_the_flag() -> None:
    client = scripted(text_message(CRISIS_REPLY))
    update = make_generate_node(client, [])(guide_state("I can't go on.", risk="crisis"))

    assert update["crisis_flagged"] is True


def test_other_replies_leave_the_flag_alone() -> None:
    client = scripted(text_message("Hello again."))
    state = guide_state("Hi", register="social", crisis_flagged=True)
    update = make_generate_node(client, [])(state)

    assert "crisis_flagged" not in update


@pytest.mark.parametrize("register", ["pointing", "explanatory", "social", "off_topic"])
def test_unsure_risk_takes_the_crisis_path_whatever_the_register(register: str) -> None:
    client = scripted(text_message(CRISIS_REPLY))
    make_generate_node(client, [])(guide_state("Hm.", risk="unsure", register=register))

    assert client.requests[0]["system"] == PARTS["5b"]


def test_a_crisis_reply_with_an_invented_number_is_written_again_once() -> None:
    invented = text_message("Please call 911 or your local emergency number now.")
    client = scripted(invented, text_message(CRISIS_REPLY))
    update = make_generate_node(client, [])(guide_state("I can't go on.", risk="crisis"))

    assert len(client.requests) == 2
    assert update["messages"][0].content == CRISIS_REPLY


def test_a_second_invented_number_is_kept_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    invented = text_message("Please call 112 now. I am staying with you.")
    client = scripted(invented, invented)
    with caplog.at_level(logging.WARNING):
        make_generate_node(client, [])(guide_state("I can't go on.", risk="crisis"))

    assert len(client.requests) == 2
    assert "Reply check failed: invents_number (crisis)" in caplog.text


def test_a_crisis_reply_without_help_is_written_again_once() -> None:
    pointless = text_message("I am here. Are you thinking of ending your life?")
    client = scripted(pointless, text_message(CRISIS_REPLY))
    update = make_generate_node(client, [])(guide_state("I can't go on.", risk="crisis"))

    assert len(client.requests) == 2
    assert client.requests[0] == client.requests[1]
    assert update["messages"][0].content == CRISIS_REPLY


def test_a_second_reply_without_help_is_kept_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    pointless = text_message("I am here. Are you thinking of ending your life?")
    client = scripted(pointless, pointless)
    with caplog.at_level(logging.WARNING):
        update = make_generate_node(client, [])(guide_state("I can't go on.", risk="crisis"))

    assert len(client.requests) == 2
    assert update["messages"][0].content == pointless.content[0].text
    assert "Reply check failed: lacks_help (crisis)" in caplog.text


def test_a_verified_number_counts_as_help() -> None:
    client = scripted(text_message("You can call 11 22 now. I am staying with you."))
    state = guide_state("I can't go on.", risk="crisis", language="sv")
    make_generate_node(client, [SWEDISH_LINE])(state)

    assert len(client.requests) == 1


@pytest.mark.parametrize(
    ("language", "expected"), [("sv", "sv"), ("en", "en"), ("de", "en"), (None, "en")]
)
def test_decline_is_in_the_persons_language_or_english(
    language: str | None, expected: str
) -> None:
    state = guide_state("Write me a poem.", register="off_topic", language=language)
    assert decline_node(state)["messages"][0].content == DECLINES[expected]
