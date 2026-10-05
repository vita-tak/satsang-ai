"""
The intro's example prompts on mocks: none may trip the keyword safety net or the treatment word
list, each must fit the one-line limit, and a prompt the classifier calls none and pointing must
reach a pointing reply through retrieval. Whether the real classifier agrees is checked in the
approved real rounds (the classifier set holds the candidates and the prompts in use).
"""
import re
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage

from src.agent.checks import mentions_treatment
from src.agent.graph import build_graph, guide_reply
from src.agent.safety_net import load_risk_patterns, mentions_risk
from src.config import RISK_PHRASES_DIR
from tests.fakes import StubRetriever, reply_message, route_message, scripted

PROMPT_SETS = (
    Path(__file__).resolve().parents[2] / "frontend/src/components/intro/prompt-sets.ts"
)
PATTERNS = load_risk_patterns(RISK_PHRASES_DIR)
# Each prompt must fit one line from 320px; the longest in use is 31 characters
MAX_LENGTH = 31

# Candidates that were tried to replace "I feel lost and don't know why.", which the classifier
# marked unsure: a practice difficulty, not a distress signal. The real classifier called both
# none and pointing (round R10) and the first is the one in use.
CANDIDATES = ["I never know what to look for.", "I lose focus as soon as I sit."]
CHOSEN = CANDIDATES[0]
REPLACED = "I feel lost and don\u2019t know why."


def prompts_in_use() -> list[str]:
    if not PROMPT_SETS.exists():
        pytest.skip("the frontend is not next to ai-service")
    text = PROMPT_SETS.read_text(encoding="utf-8")
    return re.findall(r'^\s+"([^"]+)",\s*$', text, flags=re.MULTILINE)


def test_the_intro_has_sixteen_prompts_in_four_sets() -> None:
    assert len(prompts_in_use()) == 16


@pytest.mark.parametrize("prompt", prompts_in_use() or CANDIDATES)
def test_an_intro_prompt_fits_and_trips_no_word_list(prompt: str) -> None:
    assert len(prompt) <= MAX_LENGTH
    assert not mentions_risk(prompt, "en", PATTERNS)
    assert not mentions_treatment(prompt)


@pytest.mark.parametrize("candidate", CANDIDATES)
def test_a_candidate_fits_and_trips_no_word_list(candidate: str) -> None:
    assert len(candidate) <= MAX_LENGTH
    assert not mentions_risk(candidate, "en", PATTERNS)
    assert not mentions_treatment(candidate)


def test_the_chosen_candidate_is_in_use_and_the_replaced_prompt_is_not() -> None:
    in_use = prompts_in_use()

    assert CHOSEN in in_use
    assert CANDIDATES[1] not in in_use
    assert REPLACED not in in_use


@pytest.mark.parametrize("candidate", CANDIDATES)
def test_a_candidate_the_classifier_calls_none_and_pointing_reaches_a_pointing_reply(
    candidate: str,
) -> None:
    retriever = StubRetriever([])
    client = scripted(route_message(), reply_message("Where does the not knowing sit?", "Where"))
    graph = build_graph(retriever, client, [], PATTERNS)
    state = graph.invoke({
        "messages": [HumanMessage(candidate)],
        "recent_directions": [],
        "crisis_flagged": False,
    })

    reply = guide_reply(state)
    assert (reply.register, reply.risk) == ("pointing", "none")
    assert retriever.queries == ["the query"]
    assert len(client.requests) == 2
