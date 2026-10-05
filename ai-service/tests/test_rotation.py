import logging

import pytest

from src.agent.nodes.generate import make_generate_node
from tests.fakes import FakeAnthropic, guide_state, reply_message, scripted


def generate(client: FakeAnthropic, recent: tuple[str, ...]) -> dict:
    state = guide_state("I keep feeling behind.", background=[], recent_directions=recent)
    return make_generate_node(client, [])(state)


def last_turn(client: FakeAnthropic, call: int) -> str:
    return client.requests[call]["messages"][-1]["content"]


def test_a_new_direction_needs_one_call_and_joins_the_last_two() -> None:
    client = scripted(reply_message("Where is it now?", "Where"))
    update = generate(client, ("Who", "Change"))

    assert len(client.requests) == 1
    assert update["direction"] == "Where"
    assert update["recent_directions"] == ["Change", "Where"]


def test_a_repeated_direction_is_written_again_once_with_the_directions_forbidden() -> None:
    client = scripted(
        reply_message("Who is it that feels behind?", "Who"),
        reply_message("Where is the feeling of being behind?", "Where"),
    )
    update = generate(client, ("Who", "Change"))

    assert len(client.requests) == 2
    assert "Directions used in the last two replies: Who, Change." in last_turn(client, 0)
    assert "Forbidden directions for this reply: Who, Change." in last_turn(client, 1)
    assert "Directions used in the last two replies" not in last_turn(client, 1)
    assert update["messages"][0].content == "Where is the feeling of being behind?"
    assert update["recent_directions"] == ["Change", "Where"]


def test_a_second_repeat_is_accepted_and_the_check_logs_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = scripted(
        reply_message("Who is it?", "Who"),
        reply_message("Who is behind?", "Who"),
    )
    with caplog.at_level(logging.WARNING):
        update = generate(client, ("Who", "Change"))

    assert len(client.requests) == 2
    assert update["messages"][0].content == "Who is behind?"
    assert update["recent_directions"] == ["Change", "Who"]
    assert "Reply check failed: repeats_direction (pointing)" in caplog.text


def test_a_reply_without_a_turn_is_kept_and_changes_no_direction() -> None:
    client = scripted(reply_message("That sounds heavy to carry.", "none"))
    update = generate(client, ("Who", "Change"))

    assert len(client.requests) == 1
    assert update["direction"] is None
    assert update["recent_directions"] == ["Who", "Change"]


def test_the_first_direction_starts_the_list() -> None:
    client = scripted(reply_message("What happens if you leave it alone?", "Leave alone"))
    update = generate(client, ())

    assert update["recent_directions"] == ["Leave alone"]


def test_a_question_offering_alternatives_is_logged_and_never_rewritten(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = scripted(reply_message("Is it the effort of it, or something else?", "Where"))
    with caplog.at_level(logging.WARNING):
        update = generate(client, ("Who", "Change"))

    assert len(client.requests) == 1
    assert update["messages"][0].content == "Is it the effort of it, or something else?"
    assert "Reply check failed: narrows_question (pointing)" in caplog.text


def test_text_after_the_final_question_is_logged_and_never_rewritten(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reply = "What is here when you sit? Not the quiet you remember. Just what is happening."
    client = scripted(reply_message(reply, "Where"))
    with caplog.at_level(logging.WARNING):
        update = generate(client, ("Who", "Change"))

    assert len(client.requests) == 1
    assert update["messages"][0].content == reply
    assert "Reply check failed: narrows_question (pointing)" in caplog.text
