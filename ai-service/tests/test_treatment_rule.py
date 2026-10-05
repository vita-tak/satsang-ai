"""
The treatment rule in generation: a reply to a message about a treatment or medication that
contains safe, safely, risk, risks, risky or any word starting with "meditat" is written again,
up to twice, each time naming the words it used. If the third reply still fails, a pointing or
explanatory reply is replaced by a fixed one (in the person's language) and the fallback is
logged. A crisis reply is never replaced, so that part 5b's pointer to help and direct question
stay: the best reply written is kept and the broken rule is logged by the runtime checks.
"""
import logging

import pytest

from src.agent.nodes.generate import make_generate_node
from src.agent.nodes.prompts import treatment_fallback_message
from tests.fakes import (
    CRISIS_REPLY,
    FakeAnthropic,
    guide_state,
    reply_message,
    scripted,
    text_message,
)

MESSAGE = "Should I stop my antidepressants now that I meditate every day?"
BAD_TEXT = "Meditation and medication work in different ways. Ask your doctor."
CLEAN_TEXT = "This is a question for your doctor or prescriber. I cannot answer it."
CLEAN_CRISIS = CRISIS_REPLY

# situation -> (state keyword arguments, how the model answers with a given text)
SITUATIONS = {
    "pointing": ({"register": "pointing", "background": []}, lambda text: reply_message(text)),
    "explanatory": ({"register": "explanatory", "background": []}, text_message),
    "crisis": ({"risk": "unsure"}, text_message),
}


# The situations whose failing reply is replaced by the fixed one
FALLBACK_SITUATIONS = ["pointing", "explanatory"]
CRISIS_BAD = (
    "Meditation may help. Call the emergency services. Are you thinking of ending your life?"
)
CRISIS_WORSE = (
    "Meditation is safe, and it is a risk to stop. Are you thinking of ending your life?"
)


def clean(situation: str) -> str:
    return CLEAN_CRISIS if situation == "crisis" else CLEAN_TEXT


FALLBACK_EN = (
    "That is a question for your doctor or prescriber, who knows you. I can't answer it."
)
FALLBACK_SV = (
    "Det \u00e4r en fr\u00e5ga f\u00f6r din l\u00e4kare eller f\u00f6rskrivare, som k\u00e4nner "
    "dig. Den kan jag inte svara p\u00e5."
)


def run(
    situation: str, *texts: str, message: str = MESSAGE, **state_kwargs
) -> tuple[FakeAnthropic, dict]:
    kwargs, make = SITUATIONS[situation]
    client = scripted(*(make(text) for text in texts))
    state = guide_state(message, **{**kwargs, **state_kwargs})
    return client, make_generate_node(client, [])(state)


def answer(update: dict) -> str:
    return update["messages"][0].content


@pytest.mark.parametrize("situation", SITUATIONS)
def test_a_failing_reply_is_written_again_once_and_the_clean_one_is_used(
    situation: str,
) -> None:
    client, update = run(situation, BAD_TEXT, clean(situation))

    assert len(client.requests) == 2
    assert answer(update) == clean(situation)


def last_turn(client: FakeAnthropic, call: int) -> str:
    return client.requests[call]["messages"][-1]["content"]


@pytest.mark.parametrize("situation", SITUATIONS)
def test_the_rewrite_request_differs_and_names_the_offending_words(situation: str) -> None:
    client, _ = run(situation, BAD_TEXT, clean(situation))

    assert client.requests[0] != client.requests[1]
    turn = last_turn(client, 1)
    assert 'Your previous reply used the word "meditation", which this reply must not' in turn
    assert "Write the reply again without it, and without connecting the treatment to" in turn
    assert turn.endswith("meditation.")
    assert "previous reply used" not in last_turn(client, 0)


@pytest.mark.parametrize("situation", SITUATIONS)
def test_the_rewrite_changes_nothing_but_the_last_line(situation: str) -> None:
    client, _ = run(situation, BAD_TEXT, clean(situation))
    first, second = client.requests

    assert first["system"] == second["system"]
    assert first["messages"][:-1] == second["messages"][:-1]
    assert second["messages"][-1]["content"].startswith(first["messages"][-1]["content"])


def test_several_offending_words_are_named_once_each_in_order_of_appearance() -> None:
    text = "Meditation is safe, they say. Meditating is Risky. Meditation again, and safe."
    client, _ = run("explanatory", text, CLEAN_TEXT)

    turn = last_turn(client, 1)
    assert 'used the words "meditation", "safe", "meditating" and "risky",' in turn
    assert "which this reply must not use. Write the reply again without them, and" in turn


@pytest.mark.parametrize(
    ("text", "named"),
    [("It is safe.", '"safe"'), ("Is it done safely?", '"safely"'), ("The risks.", '"risks"'),
     ("A risk.", '"risk"'), ("A risky thing.", '"risky"'), ("A meditator.", '"meditator"')],
)
def test_each_banned_word_is_named_as_it_appeared(text: str, named: str) -> None:
    client, _ = run("pointing", text, CLEAN_TEXT)
    assert named in last_turn(client, 1)


def test_a_crisis_rewrite_for_missing_help_alone_is_still_the_same_request() -> None:
    client = scripted(text_message("I am here. Are you thinking of ending your life?"),
                      text_message(CLEAN_CRISIS))
    make_generate_node(client, [])(guide_state("I can't go on.", risk="crisis"))

    assert client.requests[0] == client.requests[1]


def test_a_crisis_reply_missing_help_and_breaking_the_rule_gets_one_rewrite_naming_the_word(
) -> None:
    client = scripted(
        text_message("Meditation helps. Are you thinking of ending your life?"),
        text_message(CLEAN_CRISIS),
    )
    make_generate_node(client, [])(guide_state(MESSAGE, risk="crisis"))

    assert len(client.requests) == 2
    assert 'the word "meditation"' in last_turn(client, 1)


@pytest.mark.parametrize("situation", SITUATIONS)
def test_a_clean_reply_is_not_written_again(situation: str) -> None:
    client, update = run(situation, clean(situation))

    assert len(client.requests) == 1
    assert answer(update) == clean(situation)


SECOND_BAD = "It is risky to change it alone. Please ask your doctor, and I am here with you."
THIRD_BAD = "Many people meditate and find it safe. Ask your doctor, I am here with you."


@pytest.mark.parametrize("situation", SITUATIONS)
def test_a_second_failing_reply_is_written_again_a_second_time(situation: str) -> None:
    client, update = run(situation, BAD_TEXT, SECOND_BAD, clean(situation))

    assert len(client.requests) == 3
    assert answer(update) == clean(situation)


@pytest.mark.parametrize("situation", SITUATIONS)
def test_the_second_rewrite_names_the_words_of_the_second_reply_not_the_first(
    situation: str,
) -> None:
    client, _ = run(situation, BAD_TEXT, SECOND_BAD, clean(situation))

    assert 'the word "meditation"' in last_turn(client, 1)
    assert 'the word "risky"' in last_turn(client, 2)
    assert 'the word "meditation"' not in last_turn(client, 2)


@pytest.mark.parametrize("situation", SITUATIONS)
def test_two_rewrites_that_succeed_use_no_fallback(
    situation: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        _, update = run(situation, BAD_TEXT, SECOND_BAD, clean(situation))

    assert answer(update) == clean(situation)
    assert "Treatment fallback used" not in caplog.text


@pytest.mark.parametrize("situation", FALLBACK_SITUATIONS)
def test_a_third_failing_reply_is_replaced_by_the_fixed_reply_and_the_fallback_is_logged(
    situation: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        client, update = run(situation, BAD_TEXT, SECOND_BAD, THIRD_BAD)

    assert len(client.requests) == 3
    assert answer(update) == FALLBACK_EN
    assert f"Treatment fallback used ({situation})" in caplog.text
    assert "Reply check failed: breaks_treatment_rule" not in caplog.text


@pytest.mark.parametrize(
    ("language", "expected"),
    [("en", FALLBACK_EN), ("sv", FALLBACK_SV), ("de", FALLBACK_EN), (None, FALLBACK_EN)],
)
@pytest.mark.parametrize("situation", FALLBACK_SITUATIONS)
def test_the_fixed_reply_is_in_the_persons_language_or_english(
    situation: str, language: str | None, expected: str
) -> None:
    _, update = run(situation, BAD_TEXT, SECOND_BAD, THIRD_BAD, language=language)
    assert answer(update) == expected


def test_the_crisis_path_never_uses_the_fixed_reply_and_logs_the_broken_rule(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        client, update = run("crisis", CRISIS_BAD, CRISIS_BAD, CRISIS_BAD)

    assert len(client.requests) == 3
    assert answer(update) == CRISIS_BAD
    assert answer(update) not in (FALLBACK_EN, FALLBACK_SV)
    assert "Treatment fallback used" not in caplog.text
    assert "Reply check failed: breaks_treatment_rule (crisis)" in caplog.text


@pytest.mark.parametrize("language", ["en", "sv", None])
def test_the_crisis_path_keeps_the_direct_question_in_any_language(language: str | None) -> None:
    _, update = run("crisis", CRISIS_BAD, CRISIS_BAD, CRISIS_BAD, language=language)

    assert "Are you thinking of ending your life?" in answer(update)
    assert answer(update) != treatment_fallback_message(language)


def test_a_crisis_reply_that_ends_clean_logs_no_broken_rule(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        _, update = run("crisis", BAD_TEXT, SECOND_BAD, CLEAN_CRISIS)

    assert answer(update) == CLEAN_CRISIS
    assert "breaks_treatment_rule" not in caplog.text
    assert "Treatment fallback used" not in caplog.text


def test_the_crisis_reply_kept_is_the_one_with_the_fewest_banned_words() -> None:
    _, update = run("crisis", CRISIS_WORSE, CRISIS_BAD, CRISIS_WORSE)
    assert answer(update) == CRISIS_BAD


def test_the_crisis_reply_kept_is_the_latest_when_nothing_tells_them_apart() -> None:
    later = CRISIS_BAD.replace("Meditation", "Meditating")
    _, update = run("crisis", CRISIS_BAD, CRISIS_BAD, later)
    assert answer(update) == later


def test_a_crisis_reply_that_points_to_help_beats_a_cleaner_one_that_does_not() -> None:
    no_help = "I am with you. Are you thinking of ending your life?"
    _, update = run("crisis", CRISIS_BAD, no_help)

    assert len(update["messages"]) == 1
    assert answer(update) == CRISIS_BAD


def test_a_pointing_fallback_leaves_the_directions_untouched() -> None:
    _, update = run(
        "pointing", BAD_TEXT, SECOND_BAD, THIRD_BAD, recent_directions=("Who", "Change")
    )

    assert update["direction"] is None
    assert update["recent_directions"] == ["Who", "Change"]


def test_a_crisis_whose_rule_stays_broken_still_flags_the_crisis() -> None:
    _, update = run("crisis", CRISIS_BAD, CRISIS_BAD, CRISIS_BAD)
    assert update["crisis_flagged"] is True


def test_the_fixed_replies_are_the_owners_text_and_break_no_rule() -> None:
    from src.agent.checks import breaks_treatment_rule
    from src.agent.nodes.prompts import TREATMENT_FALLBACKS

    assert TREATMENT_FALLBACKS == {"en": FALLBACK_EN, "sv": FALLBACK_SV}
    for text in TREATMENT_FALLBACKS.values():
        assert not breaks_treatment_rule(text, MESSAGE)


def test_other_reasons_for_a_rewrite_still_get_only_one() -> None:
    client = scripted(
        text_message("I am here. Are you thinking of ending your life?"),
        text_message("I am still here. Are you thinking of ending your life?"),
    )
    update = make_generate_node(client, [])(guide_state("I can't go on.", risk="crisis"))

    assert len(client.requests) == 2
    assert answer(update) == "I am still here. Are you thinking of ending your life?"


def test_a_repeated_direction_gets_one_rewrite_even_when_it_repeats_again() -> None:
    client = scripted(reply_message(CLEAN_TEXT, "Who"), reply_message(CLEAN_TEXT, "Who"))
    state = guide_state("I feel behind.", background=[], recent_directions=("Who", "Change"))
    update = make_generate_node(client, [])(state)

    assert len(client.requests) == 2
    assert update["direction"] == "Who"


def test_a_failing_crisis_reply_that_is_also_missing_help_is_never_the_fixed_reply() -> None:
    client = scripted(
        text_message("Meditation helps. Are you thinking of ending your life?"),
        text_message("Meditate if you can. Are you thinking of ending your life?"),
        text_message("Meditation again. Are you thinking of ending your life?"),
    )
    update = make_generate_node(client, [])(guide_state(MESSAGE, risk="crisis"))

    assert len(client.requests) == 3
    assert answer(update) == "Meditation again. Are you thinking of ending your life?"


@pytest.mark.parametrize("situation", ["pointing", "explanatory"])
@pytest.mark.parametrize(
    "text", ["It is safe to ask.", "There is a risk.", "Do you meditate?", "A risky thing."]
)
def test_each_banned_word_triggers_the_rewrite(situation: str, text: str) -> None:
    client, _ = run(situation, text, CLEAN_TEXT)
    assert len(client.requests) == 2


@pytest.mark.parametrize("situation", SITUATIONS)
def test_a_message_that_is_not_about_a_treatment_is_never_rewritten(situation: str) -> None:
    client, update = run(situation, BAD_TEXT, message="I feel stuck when I meditate.")

    assert len(client.requests) == 1
    assert answer(update) == BAD_TEXT


def test_a_social_reply_is_not_checked() -> None:
    client = scripted(text_message(BAD_TEXT))
    state = guide_state(MESSAGE, register="social")
    update = make_generate_node(client, [])(state)

    assert len(client.requests) == 1
    assert answer(update) == BAD_TEXT


def test_a_repeated_direction_and_a_failing_reply_cost_one_rewrite_not_two() -> None:
    client = scripted(
        reply_message(BAD_TEXT, "Who"),
        reply_message(CLEAN_TEXT, "Where"),
    )
    state = guide_state(MESSAGE, background=[], recent_directions=("Who", "Change"))
    update = make_generate_node(client, [])(state)

    assert len(client.requests) == 2
    assert "Forbidden directions for this reply: Who, Change." in last_turn(client, 1)
    assert 'the word "meditation"' in last_turn(client, 1)
    assert answer(update) == CLEAN_TEXT


def test_a_failing_reply_with_a_new_direction_gets_no_forbidden_line_when_written_again() -> None:
    client = scripted(
        reply_message(BAD_TEXT, "Where"),
        reply_message(CLEAN_TEXT, "Where"),
    )
    state = guide_state(MESSAGE, background=[], recent_directions=("Who", "Change"))
    make_generate_node(client, [])(state)

    turn = last_turn(client, 1)
    assert "Forbidden directions" not in turn
    assert "Directions used in the last two replies: Who, Change." in turn
    assert 'the word "meditation"' in turn


def test_a_crisis_reply_missing_help_and_breaking_the_rule_is_written_again_only_once() -> None:
    client = scripted(
        text_message("Meditation helps. Are you thinking of ending your life?"),
        text_message(CLEAN_CRISIS),
    )
    update = make_generate_node(client, [])(guide_state(MESSAGE, risk="crisis"))

    assert len(client.requests) == 2
    assert answer(update) == CLEAN_CRISIS
