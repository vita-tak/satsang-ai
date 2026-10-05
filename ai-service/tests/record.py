"""
Records an approved round of real Haiku calls, so the tests can replay it for free.

Run from ai-service/, and only after the owner has approved the round:

    .venv/bin/python -m tests.record classifier --yes
    .venv/bin/python -m tests.record guide --yes
    .venv/bin/python -m tests.record guide --only risk,medical --yes
    .venv/bin/python -m tests.record classifier --only example_candidate_a --yes

--only re-records just the named scenarios or classifier cases and keeps the rest of the
existing recording.

Without --yes it says what the round would do and stops. The real key is read from .env.local
by src.config; nothing else is configured here. No retriever is built and ChromaDB is never
imported.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any

import anthropic
from anthropic.types import Message

from src.config import ANTHROPIC_API_KEY, HAIKU_MODEL
from tests.data.classifier_set import CASES
from tests.data.scenarios import SCENARIOS
from tests.fakes import request_sha256
from tests.rounds import classify_case, report, run_scenario, scenario_report

RECORDINGS = Path(__file__).resolve().parent / "recordings"


class RecordingAnthropic:
    """Passes each request to the real client and keeps its fingerprint and the response."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        self.calls: list[dict[str, Any]] = []
        self.messages = self
        self._client = client

    def create(self, **params: Any) -> Message:
        response = self._client.messages.create(**params)
        self.calls.append({
            "request_sha256": request_sha256(params),
            "response": response.model_dump(mode="json"),
        })
        return response


def record_classifier_round(only: list[str]) -> None:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    calls: dict[str, list[dict[str, Any]]] = {}
    outcomes = []
    try:
        for case in chosen_cases(only):
            recorder = RecordingAnthropic(client)
            outcomes.append(classify_case(recorder, case))
            calls[case.id] = recorder.calls
    finally:
        _save("R1 classifier set", "classifier_set.json", calls)
    print(report(outcomes))


def record_guide_round(only: list[str]) -> None:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    calls: dict[str, list[dict[str, Any]]] = {}
    outcomes = []
    try:
        for scenario in _chosen(only):
            recorder = RecordingAnthropic(client)
            outcomes.append(run_scenario(recorder, scenario))
            calls[scenario.id] = recorder.calls
    finally:
        _save("guide scenarios", "guide_scenarios.json", calls)
    print(scenario_report(outcomes))


def chosen_cases(only: list[str]) -> list[Any]:
    unknown = set(only) - {case.id for case in CASES}
    if unknown:
        sys.exit(f"Unknown classifier cases: {', '.join(sorted(unknown))}")
    return [case for case in CASES if not only or case.id in only]


def _chosen(only: list[str]) -> list[Any]:
    unknown = set(only) - {scenario.id for scenario in SCENARIOS}
    if unknown:
        sys.exit(f"Unknown scenarios: {', '.join(sorted(unknown))}")
    return [scenario for scenario in SCENARIOS if not only or scenario.id in only]


def _save(round_name: str, file_name: str, calls: dict[str, list[dict[str, Any]]]) -> None:
    """
    Write the recording, replacing only the given entries in a file that already exists. This
    runs even when a round fails part way (it is called from a finally block), so every scenario
    that finished is kept and the money already spent is not lost; a scenario that did not
    finish is never saved.
    """
    if not calls:
        return
    path = RECORDINGS / file_name
    today = datetime.date.today().isoformat()
    recording = {"round": round_name, "model": HAIKU_MODEL, "recorded": today, "calls": {}}
    if path.exists():
        recording = json.loads(path.read_text(encoding="utf-8"))
        recording["updated"] = f"{today}: {len(calls)} entries"
    recording["calls"].update(calls)
    path.write_text(json.dumps(recording, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Recorded {sum(len(c) for c in calls.values())} calls to {path}\n")


ROUNDS = {"classifier": record_classifier_round, "guide": record_guide_round}


def minimum_calls(round_name: str, only: list[str]) -> int:
    """
    The classifier set makes one call per case. The guide round makes one classifier call per
    scenario and one generation call for every scenario but the declines; a repeated direction
    or a crisis reply written again adds one more.
    """
    if round_name == "classifier":
        return len(chosen_cases(only))
    chosen = _chosen(only)
    return len(chosen) + sum("off_topic" not in s.situations for s in chosen)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record an approved round of real calls.")
    parser.add_argument("round", choices=sorted(ROUNDS))
    parser.add_argument("--only", default="", help="comma-separated ids to re-record")
    parser.add_argument("--yes", action="store_true", help="make the real calls")
    args = parser.parse_args()
    only = [name for name in args.only.split(",") if name]
    if not args.yes:
        print(f"The {args.round} round makes at least {minimum_calls(args.round, only)} real "
              "Haiku calls. Add --yes to run it.")
        sys.exit(1)
    ROUNDS[args.round](only)


if __name__ == "__main__":
    main()
