from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.nodes.generate import make_generate_node
from src.agent.nodes.prompts import ASSEMBLY, CRISIS_FLAG_LINE, PARTS, REPLY_TOOL, system_prompt
from src.config import HISTORY_LIMIT
from tests.fakes import CRISIS_REPLY, guide_state, scripted, text_message, tool_message

POINTING_REPLY = tool_message("reply", {"text": "Where is it now?", "direction": "Where"})
TEXT_REPLY = text_message("A plain reply.")


def request_for(state: dict[str, Any]) -> dict[str, Any]:
    """The one request the generation node sends for this state."""
    if state["risk"] != "none":
        response = text_message(CRISIS_REPLY)
    elif state["register"] == "pointing":
        response = POINTING_REPLY
    else:
        response = TEXT_REPLY
    client = scripted(response)
    make_generate_node(client, [])(state)
    (request,) = client.requests
    return request


def last_turn(request: dict[str, Any]) -> str:
    return request["messages"][-1]["content"]


def test_assembly_table_matches_the_guide_prompt() -> None:
    assert ASSEMBLY == {
        "pointing": ("1", "2a", "4"),
        "explanatory": ("1", "2b"),
        "social": ("1", "5a"),
        "crisis": ("5b",),
    }


@pytest.mark.parametrize(("situation", "parts"), ASSEMBLY.items())
def test_system_prompt_is_exactly_the_listed_parts(
    situation: str, parts: tuple[str, ...]
) -> None:
    prompt = system_prompt(situation)
    assert prompt == "\n\n".join(PARTS[part] for part in parts)
    for part in set(PARTS) - set(parts):
        assert PARTS[part] not in prompt


def test_pointing_call_gets_its_parts_the_reply_tool_and_its_facts() -> None:
    state = guide_state(
        "I feel behind.", background=["Answer: Rest."], recent_directions=("Who",)
    )
    request = request_for(state)

    assert request["system"] == system_prompt("pointing")
    assert request["tools"] == [REPLY_TOOL]
    assert last_turn(request) == (
        "Retrieved context:\n\nAnswer: Rest.\n\n---\n\n"
        "The person's message:\nI feel behind.\n\n---\n\n"
        "Language of the person's message: en.\n"
        "Directions used in the last two replies: Who.\n"
        "Ask at most one question."
    )


def test_pointing_call_with_no_directions_yet_says_so() -> None:
    request = request_for(guide_state("I feel behind.", background=[]))
    assert "Directions used in the last two replies: none yet." in last_turn(request)


def test_explanatory_call_gets_its_parts_and_context_but_no_directions() -> None:
    state = guide_state(
        "What does vichara mean?",
        register="explanatory",
        background=["Answer: Looking into oneself."],
    )
    request = request_for(state)

    assert request["system"] == system_prompt("explanatory")
    assert "tools" not in request
    assert last_turn(request) == (
        "Retrieved context:\n\nAnswer: Looking into oneself.\n\n---\n\n"
        "The person's message:\nWhat does vichara mean?\n\n---\n\n"
        "Language of the person's message: en.\n"
        "Ask at most one question."
    )


def test_insufficient_context_is_stated_plainly() -> None:
    state = guide_state("What is quantum physics?", register="explanatory", background=[])
    assert last_turn(request_for(state)).startswith(
        "Retrieved context: none that speaks to this message with confidence.\n\n---\n\n"
    )


def test_social_call_gets_its_parts_and_no_context() -> None:
    request = request_for(guide_state("Hello!", register="social", language="sv"))

    assert request["system"] == system_prompt("social")
    assert last_turn(request) == (
        "The person's message:\nHello!\n\n---\n\nLanguage of the person's message: sv."
    )


def test_crisis_call_gets_only_part_5b_and_the_verified_lines() -> None:
    request = request_for(guide_state("I can't go on.", risk="crisis"))

    assert request["system"] == PARTS["5b"]
    assert last_turn(request) == (
        "The person's message:\nI can't go on.\n\n---\n\n"
        "Language of the person's message: en.\n"
        "Verified crisis lines for this language: none. Name no phone number. Follow step 3 for "
        "when no number is provided."
    )


@pytest.mark.parametrize(
    "state",
    [
        guide_state("I feel behind.", background=[], crisis_flagged=True),
        guide_state(
            "What is vichara?", register="explanatory", background=[], crisis_flagged=True
        ),
        guide_state("Thank you.", register="social", crisis_flagged=True),
        guide_state("It is back again.", risk="unsure", crisis_flagged=True),
    ],
)
def test_every_call_is_told_when_a_crisis_was_flagged_earlier(state: dict[str, Any]) -> None:
    assert CRISIS_FLAG_LINE in last_turn(request_for(state))


def test_no_call_mentions_a_crisis_that_was_not_flagged() -> None:
    assert CRISIS_FLAG_LINE not in last_turn(request_for(guide_state("Hello", register="social")))


def test_an_unknown_language_adds_no_language_line() -> None:
    request = request_for(guide_state("Hello", register="social", language=None))
    assert "Language of the person's message" not in last_turn(request)


def test_history_is_the_last_ten_earlier_messages_starting_with_the_person() -> None:
    history = tuple(
        HumanMessage(f"question {i}") if i % 2 == 0 else AIMessage(f"answer {i}")
        for i in range(14)
    )
    request = request_for(guide_state("Hello", register="social", history=history))

    earlier = request["messages"][:-1]
    assert len(earlier) == HISTORY_LIMIT
    assert earlier[0] == {"role": "user", "content": "question 4"}
    assert earlier[-1] == {"role": "assistant", "content": "answer 13"}
