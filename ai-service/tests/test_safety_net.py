import pytest

from src.agent.safety_net import load_risk_patterns, mentions_risk
from src.config import RISK_PHRASES_DIR

PATTERNS = load_risk_patterns(RISK_PHRASES_DIR)


def test_a_list_is_loaded_for_each_language_file() -> None:
    assert set(PATTERNS) == {"en", "sv"}


@pytest.mark.parametrize(
    "message",
    [
        "Sometimes I want to kill myself.",
        "I DON'T WANT TO LIVE like this",
        "i dont want to live anymore",
        "I don\u2019t want to wake up tomorrow.",
        "My chest pain is getting worse and I can't breathe.",
        "I'm having a panic attack right now.",
        "He hits me when he drinks.",
    ],
)
def test_english_phrases_match_whatever_the_case_or_apostrophe(message: str) -> None:
    assert mentions_risk(message, "en", PATTERNS)


@pytest.mark.parametrize(
    "message",
    [
        "How do I let the ego die?",
        "I want the sense of a separate self to disappear.",
        "Can inquiry help with panic attacks?",
        "This practice has real skill, myself included.",
        "What do you mean by the death of the mind?",
    ],
)
def test_english_practice_talk_does_not_match(message: str) -> None:
    assert not mentions_risk(message, "en", PATTERNS)


@pytest.mark.parametrize(
    "message",
    ["Jag vill inte leva längre.", "Jag har tänkt på självmord.", "Han slår mig ibland."],
)
def test_swedish_phrases_match_for_swedish(message: str) -> None:
    assert mentions_risk(message, "sv", PATTERNS)


def test_swedish_idiom_for_noticing_does_not_match() -> None:
    assert not mentions_risk("Det slår mig att jag alltid väntar på något.", "sv", PATTERNS)


def test_the_list_follows_the_detected_language() -> None:
    assert not mentions_risk("Jag vill inte leva längre.", "en", PATTERNS)


@pytest.mark.parametrize("language", ["de", None])
def test_a_language_without_a_list_falls_back_to_english(language: str | None) -> None:
    assert mentions_risk("I want to end my life.", language, PATTERNS)
