import anthropic
from langchain_core.messages import AIMessage

from src.agent.state import SatsangState
from src.config import ANTHROPIC_API_KEY, HAIKU_MODEL

SATSANG_SYSTEM = """\
You are a guide in the tradition of Ramana Maharshi, helping seekers with \
the practice of self-inquiry (atma vichara).

Always begin by grounding your response in a direct quote from the provided passages. \
You may explain and contextualise the teachings, but never introduce ideas that \
cannot be traced back to the source texts.

Keep responses concise and contemplative. Point always toward direct investigation \
of the Self. End with a single follow-up question that invites the seeker to go deeper."""

PERSONAL_STRUGGLE_SYSTEM = """\
You are a compassionate guide in the tradition of Ramana Maharshi, \
sitting with a seeker who is sharing a difficulty or pain.

Begin by acknowledging what has been shared. Then, gently offer a passage \
from the teachings that speaks to their situation. Never dismiss the struggle. \
End with a single open question that invites the seeker to be with their own experience."""

GUIDED_INQUIRY_SYSTEM = """\
You are guiding a seeker in the direct practice of self-inquiry in the \
tradition of Ramana Maharshi.

Do not quote from texts. Work only with what the seeker has shared. \
Give a direct pointing toward the investigation of 'Who am I?' \
Use simple, clear language. End with a single question that points them inward."""

DECLINE_MESSAGE = (
    "This is a space for self-inquiry and the teachings of Ramana Maharshi. "
    "I am not able to help with that here. "
    "Is there something about the practice or the teachings you would like to explore?"
)


def _rag_prompt(state: SatsangState) -> str:
    """Build the user prompt that combines retrieved context with the seeker's question."""
    return (
        f"Relevant passages from the teachings:\n\n{state['retrieved_context']}\n\n"
        f"---\n\nSeeker's question: {state['messages'][-1].content}"
    )


def _history(state: SatsangState) -> list[dict]:
    """Convert conversation history to Anthropic message format."""
    return [
        {"role": "user" if m.type == "human" else "assistant", "content": m.content}
        for m in state["messages"]
    ]


def make_generate_node(system_prompt: str):
    """
    Factory that returns a generate node for RAG-based responses.
    Used for satsang, definition, and personal_struggle intents.
    """
    def generate_node(state: SatsangState) -> dict:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": _rag_prompt(state)}],
        )
        return {"messages": [AIMessage(content=response.content[0].text)]}

    return generate_node


def guided_inquiry_node(state: SatsangState) -> dict:
    """
    Direct self-inquiry guidance. No RAG -- works with conversation history only,
    so the guide can track where the seeker is in the practice within this session.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        system=GUIDED_INQUIRY_SYSTEM,
        messages=_history(state),
    )
    return {"messages": [AIMessage(content=response.content[0].text)]}


def decline_node(state: SatsangState) -> dict:
    """Politely redirects off-topic requests back to the teachings."""
    return {"messages": [AIMessage(content=DECLINE_MESSAGE)]}