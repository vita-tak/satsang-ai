import logging
from collections.abc import Callable

import anthropic
from langchain_core.messages import AIMessage

from src.agent.checks import (
    CheckedReply,
    failed_checks,
    invents_number,
    lacks_help,
    treatment_rule_words,
)
from src.agent.crisis_lines import CrisisLine, lines_for_language
from src.agent.nodes.prompts import (
    CRISIS_FLAG_LINE,
    NO_DIRECTION,
    ONE_QUESTION_LINE,
    REPLY_TOOL,
    avoid_words_line,
    crisis_lines_block,
    decline_message,
    directions_line,
    forbidden_directions_line,
    language_line,
    system_prompt,
    treatment_fallback_message,
    user_turn,
)
from src.agent.state import Direction, GuideState, Situation
from src.config import HAIKU_MODEL, HISTORY_LIMIT, MAX_TREATMENT_REWRITES, REPLY_MAX_TOKENS

logger = logging.getLogger(__name__)


def situation_of(state: GuideState) -> Situation:
    """The assembly table's row for this message: crisis whenever there is any risk."""
    return "crisis" if state["risk"] != "none" else state["register"]


def make_generate_node(
    client: anthropic.Anthropic, crisis_lines: list[CrisisLine]
) -> Callable[[GuideState], dict]:
    """
    Factory that captures the Anthropic client and the verified crisis lines, both built once at
    startup.

    The system prompt is the assembly table's parts for the situation and nothing else; the
    retrieved context, the message and the dynamic facts make up the last user turn. A pointing
    reply reports the direction of its turn. A reply is written again, once, when it repeats one
    of the last two directions or (crisis only) when it points to no help or invents a number;
    the second reply is kept whatever it says. A reply that breaks the treatment rule is written
    again up to `MAX_TREATMENT_REWRITES` times, each rewrite naming the banned words the reply
    before it used. If the reply after the last rewrite still breaks the rule, a pointing or
    explanatory reply is replaced by a fixed one in the person's language and the fallback is
    logged. A crisis reply is never replaced, because part 5b's pointer to help and direct
    question must stay: the best of its replies is kept. Every reply then goes through the
    runtime checks, which log what is still wrong, a kept crisis reply's broken rule included.
    """
    def generate_node(state: GuideState) -> dict:
        situation = situation_of(state)
        if situation == "pointing":
            update = _pointing_reply(client, state)
        else:
            update = _plain_reply(client, state, situation, crisis_lines)
        _log_failed_checks(state, situation, update, crisis_lines)
        return update

    return generate_node


def decline_node(state: GuideState) -> dict:
    """The fixed decline for an off-topic message, in the person's language; no model call."""
    return {"messages": [AIMessage(content=decline_message(state["language"]))]}


def _pointing_reply(client: anthropic.Anthropic, state: GuideState) -> dict:
    recent = state["recent_directions"]
    text, direction = _ask_pointing(client, state, directions_line(recent))
    rewrites = 0
    while rewrites < MAX_TREATMENT_REWRITES:
        avoid = _avoid_line(text, state)
        # A repeated direction earns one rewrite; only the treatment rule earns a second
        if not (avoid or (direction in recent and rewrites == 0)):
            break
        in_recent = direction in recent
        facts = forbidden_directions_line(recent) if in_recent else directions_line(recent)
        text, direction = _ask_pointing(client, state, facts, avoid)
        rewrites += 1
    if _breaks_treatment_rule(text, state, "pointing"):
        return _fallback_update(state, "pointing", recent)
    return {
        "messages": [AIMessage(content=text)],
        "direction": direction,
        "recent_directions": _rotated(recent, direction),
    }


def _ask_pointing(
    client: anthropic.Anthropic,
    state: GuideState,
    directions_fact: str,
    avoid_line: str | None = None,
) -> tuple[str, Direction | None]:
    """One pointing call: the reply text and the direction the model reports for its turn."""
    facts = _facts(state, "pointing", [], directions_fact, avoid_line)
    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=REPLY_MAX_TOKENS["pointing"],
        system=system_prompt("pointing"),
        tools=[REPLY_TOOL],
        tool_choice={"type": "tool", "name": REPLY_TOOL["name"]},
        messages=_messages(state, facts, state.get("background", [])),
    )
    reply = next(block for block in response.content if block.type == "tool_use").input
    direction = None if reply["direction"] == NO_DIRECTION else reply["direction"]
    return reply["text"], direction


def _rotated(recent: list[Direction], direction: Direction | None) -> list[Direction]:
    """The last two directions after this reply. A reply without a turn changes nothing."""
    if direction is None:
        return recent
    return [*recent, direction][-2:]


def _plain_reply(
    client: anthropic.Anthropic,
    state: GuideState,
    situation: Situation,
    crisis_lines: list[CrisisLine],
) -> dict:
    """
    An explanatory, social or crisis reply, written as plain text. A crisis reply that does not
    point to real help, or that names a number not on the verified list, is written again once:
    part 5b puts real help before anything but presence and the direct question, and a made-up
    number is never acceptable. A reply that breaks the treatment rule is written again, up to
    `MAX_TREATMENT_REWRITES` times, in any of these situations the rule applies to. If it still
    breaks it, an explanatory reply becomes the fixed treatment reply; a crisis reply never does,
    since that would drop the pointer to help and the direct question, so the best reply written
    is kept and the runtime checks log the broken rule.
    """
    first = _plain_request(state, situation, crisis_lines)
    texts = [client.messages.create(**first).content[0].text]
    rewrites = 0
    while rewrites < MAX_TREATMENT_REWRITES and _needs_rewrite(
        texts[-1], state, situation, crisis_lines, first_pass=rewrites == 0
    ):
        rewrite = _plain_request(state, situation, crisis_lines, _avoid_line(texts[-1], state))
        texts.append(client.messages.create(**rewrite).content[0].text)
        rewrites += 1
    if situation == "crisis":
        text = _best_crisis_reply(texts, state, crisis_lines)
    elif _breaks_treatment_rule(texts[-1], state, situation):
        logger.warning("Treatment fallback used (%s)", situation)
        text = treatment_fallback_message(state["language"])
    else:
        text = texts[-1]
    update: dict = {"messages": [AIMessage(content=text)]}
    if situation == "crisis":
        # Once set, the flag stays for the rest of the session
        update["crisis_flagged"] = True
    return update


def _plain_request(
    state: GuideState,
    situation: Situation,
    crisis_lines: list[CrisisLine],
    avoid_line: str | None = None,
) -> dict:
    background = state.get("background", []) if situation == "explanatory" else None
    facts = _facts(state, situation, crisis_lines, avoid_line=avoid_line)
    return {
        "model": HAIKU_MODEL,
        "max_tokens": REPLY_MAX_TOKENS[situation],
        "system": system_prompt(situation),
        "messages": _messages(state, facts, background),
    }


def _needs_rewrite(
    text: str,
    state: GuideState,
    situation: Situation,
    crisis_lines: list[CrisisLine],
    first_pass: bool,
) -> bool:
    """Missing help or a made-up number earns one rewrite; the treatment rule can earn more."""
    if first_pass and situation == "crisis" and _misses_help(text, crisis_lines):
        return True
    return _breaks_treatment_rule(text, state, situation)


def _best_crisis_reply(
    texts: list[str], state: GuideState, crisis_lines: list[CrisisLine]
) -> str:
    """
    The crisis reply to keep: one that points to real help comes first, then the one with the
    fewest banned treatment words, then the latest. Real help outranks the treatment rule.
    """
    message = state["messages"][-1].content
    return min(
        reversed(texts),
        key=lambda text: (
            _misses_help(text, crisis_lines),
            len(treatment_rule_words(text, message)),
        ),
    )


def _fallback_update(state: GuideState, situation: Situation, recent: list[Direction]) -> dict:
    """The fixed treatment reply for a pointing message: no turn, so the directions stand."""
    logger.warning("Treatment fallback used (%s)", situation)
    return {
        "messages": [AIMessage(content=treatment_fallback_message(state["language"]))],
        "direction": None,
        "recent_directions": recent,
    }


def _breaks_treatment_rule(text: str, state: GuideState, situation: Situation) -> bool:
    """Whether the reply breaks the treatment rule, which social replies are exempt from."""
    return situation != "social" and _avoid_line(text, state) is not None


def _misses_help(text: str, crisis_lines: list[CrisisLine]) -> bool:
    numbers = [line.number for line in crisis_lines]
    return lacks_help(text, numbers) or invents_number(text, numbers)


def _avoid_line(text: str, state: GuideState) -> str | None:
    """The line that names the banned treatment words in a reply, or None when it has none."""
    words = treatment_rule_words(text, state["messages"][-1].content)
    return avoid_words_line(words) if words else None


def _facts(
    state: GuideState,
    situation: Situation,
    crisis_lines: list[CrisisLine],
    directions_fact: str | None = None,
    avoid_line: str | None = None,
) -> list[str]:
    """The dynamic inputs of one call, in the order the guide prompt lists them."""
    facts = []
    if state["language"]:
        facts.append(language_line(state["language"]))
    if directions_fact:
        facts.append(directions_fact)
    if state["crisis_flagged"]:
        facts.append(CRISIS_FLAG_LINE)
    if situation == "crisis":
        facts.append(crisis_lines_block(lines_for_language(crisis_lines, state["language"])))
    if situation in ("pointing", "explanatory"):
        facts.append(ONE_QUESTION_LINE)
    if avoid_line:
        facts.append(avoid_line)
    return facts


def _messages(state: GuideState, facts: list[str], background: list[str] | None) -> list[dict]:
    """The recent earlier turns, then the new user turn."""
    content = user_turn(state["messages"][-1].content, facts, background)
    return _history(state) + [{"role": "user", "content": content}]


def _history(state: GuideState) -> list[dict]:
    """Recent earlier turns in Anthropic message format, without the new message."""
    earlier = state["messages"][:-1][-HISTORY_LIMIT:]
    return [
        {"role": "user" if m.type == "human" else "assistant", "content": m.content}
        for m in earlier
    ]


def _log_failed_checks(
    state: GuideState, situation: Situation, update: dict, crisis_lines: list[CrisisLine]
) -> None:
    reply = CheckedReply(
        text=update["messages"][0].content,
        situation=situation,
        person_words="\n".join(m.content for m in state["messages"] if m.type == "human"),
        message=state["messages"][-1].content,
        passages=tuple(state.get("copy_sources", [])),
        direction=update.get("direction"),
        recent_directions=tuple(state["recent_directions"]),
        allowed_numbers=tuple(line.number for line in crisis_lines),
    )
    for name in failed_checks(reply):
        # The check's name only: the reply and the person's words are never logged
        logger.warning("Reply check failed: %s (%s)", name, situation)
