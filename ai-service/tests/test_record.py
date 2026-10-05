"""The recorder's choice of what to run, without making any call."""
import pytest

from tests.data.classifier_set import CASES
from tests.record import chosen_cases, minimum_calls


def test_the_classifier_round_runs_every_case_by_default() -> None:
    assert chosen_cases([]) == CASES
    assert minimum_calls("classifier", []) == len(CASES)


def test_the_classifier_round_can_run_chosen_cases_only() -> None:
    only = ["example_candidate_a", "example_candidate_b"]

    assert [case.id for case in chosen_cases(only)] == only
    assert minimum_calls("classifier", only) == 2


def test_an_unknown_classifier_case_stops_the_round_before_any_call() -> None:
    with pytest.raises(SystemExit):
        chosen_cases(["no_such_case"])
