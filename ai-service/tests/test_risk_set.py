"""
Replays the classifier set (round R1 and later) for free. Every case that has a recording is
replayed; a case added since the last round is reported as skipped until a round records it. The
whole replay is skipped as stale once the classifier's prompt changes.
"""
import json
from pathlib import Path

import pytest

from tests.data.classifier_set import CASES
from tests.fakes import StaleRecording, replaying
from tests.rounds import Outcome, classify_case, report

RECORDING = Path(__file__).resolve().parent / "recordings" / "classifier_set.json"


@pytest.fixture(scope="module")
def outcomes() -> list[Outcome]:
    if not RECORDING.exists():
        pytest.skip("round R1 has not been recorded")
    recorded = recorded_cases()
    calls = json.loads(RECORDING.read_text(encoding="utf-8"))["calls"]
    try:
        results = [classify_case(replaying(calls[case.id]), case) for case in recorded]
    except StaleRecording:
        pytest.skip("the recording is stale: the classifier or a case changed since it was made")
    print("\n" + report(results))
    return results


def recorded_cases() -> list:
    """The cases that have a recording; an empty list when there is no recording at all."""
    if not RECORDING.exists():
        return []
    calls = json.loads(RECORDING.read_text(encoding="utf-8"))["calls"]
    return [case for case in CASES if case.id in calls]


def test_every_case_in_the_set_has_a_recording() -> None:
    missing = [case.id for case in CASES if case not in recorded_cases()]
    if missing:
        pytest.skip(f"not recorded yet, waiting for an approved round: {', '.join(missing)}")


def test_every_risk_case_is_flagged(outcomes: list[Outcome]) -> None:
    missed = [o.case.id for o in outcomes if o.case.should_flag and not o.flagged]
    assert missed == []


# Misses found in a round and not fixed yet. Strict: the test fails if one of them goes away or a
# new one appears, so the list has to be kept true. Empty after round R8: `who_dies` left when the
# owner changed its expected register, and `personal_book` stopped being declined once the
# classifier text said a request about the practice is never off-topic.
KNOWN_MISSES: dict[str, list[str]] = {}


def test_off_topic_and_personal_messages_get_the_expected_register(
    outcomes: list[Outcome],
) -> None:
    wrong = {o.case.id: o.problems for o in outcomes if not o.case.should_flag and o.problems}
    assert wrong == KNOWN_MISSES


def test_the_language_is_detected(outcomes: list[Outcome]) -> None:
    wrong = [o.case.id for o in outcomes if o.language != o.case.language]
    assert wrong == []
