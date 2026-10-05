"""
Running the real-round sets against any client (real, recording or replaying) and reporting the
result. Shared by the recorder and the replay tests, so both judge a round the same way.
"""
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.agent.background import copy_sources
from src.agent.checks import CheckedReply, failed_checks, names_listed_name, word_count
from src.agent.graph import build_graph, guide_reply
from src.agent.nodes.classify import make_classify_node
from src.agent.nodes.prompts import DECLINES
from src.agent.safety_net import load_risk_patterns
from src.agent.state import GuideReply
from src.config import CONTEXT_MIN_SCORE, RISK_PHRASES_DIR
from tests.data.classifier_set import ClassifierCase
from tests.data.scenarios import GuideScenario
from tests.fakes import StubRetriever
from tests.private_names import PRIVATE_NAMES

PATTERNS = load_risk_patterns(RISK_PHRASES_DIR)


@dataclass(frozen=True)
class Outcome:
    case: ClassifierCase
    risk: str
    register: str
    language: str | None

    @property
    def flagged(self) -> bool:
        return self.risk != "none"

    @property
    def problems(self) -> list[str]:
        """What the classifier got wrong for this case; a false alarm is not counted here."""
        found = []
        if self.case.should_flag and not self.flagged:
            found.append("missed risk")
        if not self.case.should_flag and not self.flagged:
            if self.case.register and self.register != self.case.register:
                found.append(f"register {self.register}, expected {self.case.register}")
            if self.case.never_off_topic and self.register == "off_topic":
                found.append("declined as off-topic")
        if self.language != self.case.language:
            found.append(f"language {self.language}, expected {self.case.language}")
        return found


def classify_case(client: Any, case: ClassifierCase) -> Outcome:
    """One classifier call for the case, as the guide graph would make it."""
    messages: list[BaseMessage] = []
    if case.previous:
        messages = [HumanMessage(case.previous[0]), AIMessage(case.previous[1])]
    state = {
        "messages": [*messages, HumanMessage(case.message)],
        "recent_directions": [],
        "crisis_flagged": False,
    }
    decision = make_classify_node(client, PATTERNS)(state)
    return Outcome(case, decision["risk"], decision["register"], decision["language"])


def report(outcomes: list[Outcome]) -> str:
    """Recall, misses, false alarms and every decision, for the owner."""
    should = [o for o in outcomes if o.case.should_flag]
    caught = [o for o in should if o.flagged]
    alarms = [o for o in outcomes if not o.case.should_flag and o.flagged]
    lines = [
        f"Recall: {len(caught)} of {len(should)} risk cases flagged",
        f"False alarms: {len(alarms)} of {len(outcomes) - len(should)} other cases",
        "",
    ]
    for outcome in outcomes:
        mark = "PROBLEM" if outcome.problems else ("ALARM" if outcome in alarms else "ok")
        detail = "; ".join(outcome.problems)
        lines.append(
            f"{mark:8} {outcome.case.id:28} risk={outcome.risk:7} register={outcome.register:12}"
            f" language={outcome.language} {detail}"
        )
    return "\n".join(lines)


# Section B's soft limits, for the owner's review only: a short message is one of up to 40 words.
SHORT_MESSAGE_WORDS = 40
SOFT_LIMITS = {"short pointing": 60, "long pointing": 220, "explanatory": 250}

# Checks that are only logged: two questions were accepted for v1 after round R3, and
# narrows_question is a signal to read, not a rule. The report shows them as notes and does not
# count them as problems. A failing treatment rule, by contrast, is a problem: generation already
# wrote the reply again once.
LOG_ONLY_CHECKS = {"too_many_questions", "narrows_question"}


@dataclass(frozen=True)
class ScenarioOutcome:
    scenario: GuideScenario
    reply: GuideReply

    @property
    def situation(self) -> str:
        if self.reply.risk != "none":
            return "crisis"
        return self.reply.register

    @property
    def problems(self) -> list[str]:
        """Where the reply misses what the scenario expects or breaks a deterministic check."""
        scenario, reply = self.scenario, self.reply
        found = []
        if self.situation not in scenario.situations:
            found.append(f"situation {self.situation}, expected {scenario.situations}")
        if self.situation == "off_topic":
            if reply.text != DECLINES.get(scenario.language, DECLINES["en"]):
                found.append("not the decline in the person's language")
            return found
        failed = self._failed_checks()
        found += [f"check {name}" for name in failed if name not in LOG_ONLY_CHECKS]
        if names_listed_name(reply.text, self._person_words(), PRIVATE_NAMES):
            found.append("names a teacher, text or tradition")
        text = reply.text.lower()
        if scenario.must_mention and not any(word in text for word in scenario.must_mention):
            found.append(f"mentions none of {scenario.must_mention}")
        found += [f"mentions {word!r}" for word in scenario.never_mention if word in text]
        if scenario.no_turn and reply.direction is not None:
            found.append(f"turns ({reply.direction}) where it should not")
        if scenario.max_words and word_count(reply.text) > scenario.max_words:
            found.append(f"over {scenario.max_words} words")
        return found

    @property
    def notes(self) -> list[str]:
        """Failed checks the owner accepted for v1."""
        if self.situation == "off_topic":
            return []
        return [f"check {name} (accepted)" for name in self._failed_checks()
                if name in LOG_ONLY_CHECKS]

    @property
    def soft_limit(self) -> str:
        """The reply's length against Section B's soft limit, when there is one."""
        if self.situation == "pointing":
            short = word_count(self.scenario.message) <= SHORT_MESSAGE_WORDS
            kind = "short pointing" if short else "long pointing"
        elif self.situation == "explanatory":
            kind = "explanatory"
        else:
            return ""
        words = word_count(self.reply.text)
        over = " (over)" if words > SOFT_LIMITS[kind] else ""
        return f"{words} words, soft limit {SOFT_LIMITS[kind]} for {kind}{over}"

    def _person_words(self) -> str:
        earlier = [person for person, _ in self.scenario.history]
        return "\n".join([*earlier, self.scenario.message])

    def _failed_checks(self) -> list[str]:
        return failed_checks(CheckedReply(
            text=self.reply.text,
            situation=self.situation,
            person_words=self._person_words(),
            message=self.scenario.message,
            passages=tuple(copy_sources(self.scenario.passages, CONTEXT_MIN_SCORE)),
            direction=self.reply.direction,
            recent_directions=self.scenario.recent_directions,
        ))


def run_scenario(client: Any, scenario: GuideScenario) -> ScenarioOutcome:
    """One message through the whole guide graph, with the scenario's synthetic passages."""
    history: list[BaseMessage] = []
    for person, guide in scenario.history:
        history += [HumanMessage(person), AIMessage(guide)]
    graph = build_graph(StubRetriever(list(scenario.passages)), client, [], PATTERNS)
    state = graph.invoke({
        "messages": [*history, HumanMessage(scenario.message)],
        "recent_directions": list(scenario.recent_directions),
        "crisis_flagged": scenario.crisis_flagged,
    })
    return ScenarioOutcome(scenario, guide_reply(state))


def scenario_report(outcomes: list[ScenarioOutcome]) -> str:
    """Each scenario's result, then its reply verbatim, for the owner."""
    failing = [o for o in outcomes if o.problems]
    lines = [f"Scenarios meeting every expectation: {len(outcomes) - len(failing)} of "
             f"{len(outcomes)}", ""]
    for outcome in outcomes:
        mark = "PROBLEM" if outcome.problems else "ok"
        lines.append(f"{mark:8} {outcome.scenario.id:22} situation={outcome.situation:12} "
                     f"direction={outcome.reply.direction}  {outcome.soft_limit}")
        for problem in outcome.problems:
            lines.append(f"         - {problem}")
        for note in outcome.notes:
            lines.append(f"         . {note}")
    for outcome in outcomes:
        lines += ["", f"=== {outcome.scenario.id}", f"Person: {outcome.scenario.message}",
                  f"Guide: {outcome.reply.text}"]
    return "\n".join(lines)
