import anthropic

from src.agent.state import SatsangState
from src.config import ANTHROPIC_API_KEY, HAIKU_MODEL

SYSTEM = (
    "You route messages sent to an AI guide to self-inquiry in the tradition of "
    "Ramana Maharshi. When there is a previous reply from the guide you see it too, "
    "because seekers often answer the guide's question in a word or two, and such an "
    "answer only makes sense in context."
)

# tool_use forces Haiku to return exactly one of the enum values -- no parsing needed
TOOL = {
    "name": "route_message",
    "description": (
        "Record what the seeker's new message is doing, and a standalone search query "
        "for finding the passages that speak to it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "teaching",
                    "practice",
                    "struggle",
                    "definition",
                    "social",
                    "crisis",
                    "off_topic",
                ],
                "description": (
                    "teaching: asks about the teachings or the nature of things: the Self, "
                    "the mind, the world, God, death, rebirth, experiences, other teachers, "
                    "or the guide itself. "
                    "practice: asks how to practise or to be guided now, reports what happens "
                    "in practice, or answers the guide's question. "
                    "struggle: shares a personal difficulty or pain, in life or in practice. "
                    "definition: asks what a term means, such as a Sanskrit word. "
                    "social: only greets, thanks or says goodbye. "
                    "crisis: may be at risk of harming themselves or someone else, or is in "
                    "acute danger. "
                    "off_topic: unrelated to the teachings, the practice or the seeker's inner "
                    "life. A reply to the guide's question is never off_topic."
                ),
            },
            "search_query": {
                "type": "string",
                "description": (
                    "The seeker's message as a standalone question for searching the texts, "
                    "with references to the guide's previous reply resolved. If the message "
                    "already stands alone, repeat it unchanged. A long message, such as a "
                    "letter or an account of experiences, is the exception: write the one or "
                    "two questions at its heart, in a sentence or two."
                ),
            },
        },
        "required": ["intent", "search_query"],
    },
}


def _classifier_input(state: SatsangState) -> str:
    """The seeker's new message, after the guide's previous reply when there is one."""
    messages = state["messages"]
    latest = messages[-1].content
    if len(messages) < 2:
        return f"The seeker's message:\n{latest}"
    previous = messages[-2].content
    return f"The guide's previous reply:\n{previous}\n\nThe seeker's new message:\n{latest}"


def classify_intent_node(state: SatsangState) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=256,
        system=SYSTEM,
        tools=[TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": _classifier_input(state)}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return {
        "intent": tool_use.input["intent"],
        "search_query": tool_use.input["search_query"],
    }
