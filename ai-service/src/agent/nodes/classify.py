import anthropic

from src.agent.state import SatsangState
from src.config import ANTHROPIC_API_KEY, HAIKU_MODEL

SYSTEM = (
    "You are an intent classifier for a self-inquiry guidance system "
    "in the tradition of Ramana Maharshi. Classify the user's message "
    "into exactly one of the five provided categories."
)

# tool_use forces Haiku to return exactly one of the enum values -- no parsing needed
TOOL = {
    "name": "classify_intent",
    "description": "Classify the user's message into one intent category.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["satsang", "self_inquiry", "definition", "personal_struggle", "off_topic"],
                "description": (
                    "satsang: questions about Ramana's teachings, the nature of Self, "
                    "consciousness, reality, or the path in general. "
                    "self_inquiry: seeker wants direct guidance in the practice right now. "
                    "definition: asking for the meaning of a Sanskrit term or concept. "
                    "personal_struggle: sharing a personal difficulty or obstacle in practice. "
                    "off_topic: unrelated to self-inquiry or these teachings."
                ),
            }
        },
        "required": ["intent"],
    },
}


def classify_intent_node(state: SatsangState) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=64,
        system=SYSTEM,
        tools=[TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": state["messages"][-1].content}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return {"intent": tool_use.input["intent"]}