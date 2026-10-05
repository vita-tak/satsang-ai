import re
from collections.abc import Callable

import anthropic

from src.agent.nodes.prompts import CRISIS_FLAG_LINE
from src.agent.safety_net import mentions_risk
from src.agent.state import GuideState
from src.config import CLASSIFIER_MAX_TOKENS, CLASSIFIER_TEMPERATURE, HAIKU_MODEL

SYSTEM = """\
You sort the messages that people send to an AI guide for conversations about self-inquiry. \
For each new message you record whether it signals risk, which register the guide should \
answer in, the language it is written in, and what to search for in the guide's background \
texts.

You see the new message, and before it the person's previous message and the guide's previous \
reply when there are any, because people often answer the guide in a word or two and such an \
answer only makes sense in context. A line may also say that a crisis was flagged earlier in \
the conversation; then read the new message with particular care for risk.

Risk comes before everything else. A greeting, a thanks, or a message that has nothing to do \
with self-inquiry can still carry risk, and then the risk is what counts. Missing a person who \
is at risk is far worse than a false alarm, so when you hesitate between none and another \
level, do not choose none."""

# Forced and strict, so Haiku returns exactly these four fields with valid values, nothing to
# parse. Risk comes first so the model weighs it before anything else.
TOOL = {
    "name": "route_message",
    "description": "Record how the guide should handle the person's new message.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "risk": {
                "type": "string",
                "enum": ["none", "unsure", "crisis"],
                "description": (
                    "crisis: the message suggests that the person may be thinking of ending "
                    "their life or of harming themselves, or may be in immediate danger of "
                    "another kind: a medical emergency, danger to others or a threat of "
                    "violence, abuse or violence against them, losing contact with reality "
                    "(such as hearing voices, fixed false beliefs, severe confusion, or such "
                    "experiences taken for a spiritual awakening), or acute panic. "
                    "unsure: something in the message or the conversation might point to one "
                    "of these, but you cannot tell, including indirect or veiled signs. "
                    "none: no such sign. Sorrow, grief, illness, exhaustion, and despair about "
                    "life without any sign of wanting to die are none. So is talk of the ego, "
                    "the mind or the sense of a separate self ending, dissolving or "
                    "disappearing, and so are calm reports of experiences in practice, unless "
                    "the person's body, life or safety comes into it."
                ),
            },
            "register": {
                "type": "string",
                "enum": ["pointing", "explanatory", "social", "off_topic"],
                "description": (
                    "pointing: the default. The person shares an experience, a feeling or "
                    "something from their practice, asks about themselves or their own "
                    "looking, describes a difficulty, answers the guide, or writes anything "
                    "that does not call for an explanation. "
                    "explanatory: the person asks to understand an idea: what a term or "
                    "concept means, how an idea fits together, the difference between two "
                    "ideas, what a named teacher, text or tradition held, or for a quote, a "
                    "passage or a reference. "
                    "social: only a greeting, thanks, a goodbye, or small talk that carries no "
                    "experience, question or difficulty. "
                    "off_topic: only when the message is clearly unrelated to the person, their "
                    "inner life, their practice and self-inquiry, such as a request for "
                    "unrelated information or a task. A message that says anything about the "
                    "person or how they feel is not off_topic, even when it also asks for "
                    "something unrelated. A request about meditation or the person's own "
                    "practice, including a request for resources such as a book, a course or an "
                    "app, is never off_topic. A question about consciousness, the mind, "
                    "awareness or the self, including one asked through science, is never "
                    "off_topic. This holds whatever was said before it. When unsure, choose "
                    "pointing."
                ),
            },
            "language": {
                "type": "string",
                "description": (
                    "The language the new message is written in, as a lowercase two-letter "
                    "ISO 639-1 code."
                ),
            },
            "search_query": {
                "type": "string",
                "description": (
                    "The new message as a standalone question for searching the guide's "
                    "background texts, with references to the guide's previous reply "
                    "resolved. If the message already stands alone, repeat it unchanged. A "
                    "long message, such as a letter or an account of experiences, is the "
                    "exception: write the one or two questions at its heart, in a sentence or "
                    "two."
                ),
            },
        },
        "required": ["risk", "register", "language", "search_query"],
        "additionalProperties": False,
    },
}


def make_classify_node(
    client: anthropic.Anthropic, risk_patterns: dict[str, re.Pattern[str]]
) -> Callable[[GuideState], dict]:
    """
    Factory that captures the Anthropic client and the keyword net's patterns, both built once
    at startup.

    One Haiku call decides the risk, the register, the language and the search query. The
    keyword net then reads the message on its own and can raise the risk to crisis, never lower
    it.
    """
    def classify_node(state: GuideState) -> dict:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=CLASSIFIER_MAX_TOKENS,
            system=SYSTEM,
            tools=[TOOL],
            tool_choice={"type": "tool", "name": TOOL["name"]},
            messages=[{"role": "user", "content": _classifier_input(state)}],
            extra_body={"temperature": CLASSIFIER_TEMPERATURE},
        )
        decision = next(block for block in response.content if block.type == "tool_use").input
        language = _language_code(decision["language"])
        risk = decision["risk"]
        if mentions_risk(state["messages"][-1].content, language, risk_patterns):
            risk = "crisis"
        return {
            "risk": risk,
            "register": decision["register"],
            "language": language,
            "search_query": decision["search_query"],
        }

    return classify_node


def _classifier_input(state: GuideState) -> str:
    """The new message, after the crisis flag and the last exchange when there are any."""
    messages = state["messages"]
    blocks = [CRISIS_FLAG_LINE] if state.get("crisis_flagged") else []
    if len(messages) >= 3:
        blocks.append(f"The person's previous message:\n{messages[-3].content}")
        blocks.append(f"The guide's previous reply:\n{messages[-2].content}")
    blocks.append(f"The person's new message:\n{messages[-1].content}")
    return "\n\n".join(blocks)


def _language_code(value: str) -> str | None:
    """The two-letter code, or None when the model wrote something else."""
    code = value.strip().lower()
    return code if re.fullmatch(r"[a-z]{2}", code) else None
