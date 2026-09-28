import anthropic
from langchain_core.messages import AIMessage

from src.agent.nodes.prompts import (
    DECLINE_MESSAGE,
    PASSAGES_GUIDE,
    closing_reminder,
    system_prompt,
)
from src.agent.state import SatsangState
from src.config import ANTHROPIC_API_KEY, HAIKU_MODEL

# The last five exchanges. Earlier turns come in pairs, so the window starts with the seeker.
HISTORY_LIMIT = 10


def _history(state: SatsangState) -> list[dict]:
    """Recent earlier turns in Anthropic message format, without the new message."""
    earlier = state["messages"][:-1][-HISTORY_LIMIT:]
    return [
        {"role": "user" if m.type == "human" else "assistant", "content": m.content}
        for m in earlier
    ]


def _rag_prompt(state: SatsangState) -> str:
    """
    Build the user turn that combines the retrieved passages with the seeker's new message,
    closed by the mode's reminder when it has one.
    """
    prompt = (
        f"{PASSAGES_GUIDE}\n\n"
        f"Passages:\n\n{state['retrieved_context']}\n\n"
        f"---\n\nThe seeker's message: {state['messages'][-1].content}"
    )
    reminder = closing_reminder(state["mode"], state["intent"])
    return f"{prompt}\n\n---\n\n{reminder}" if reminder else prompt


def _complete(system: str, messages: list[dict], max_tokens: int) -> str:
    """Send one request to Claude and return the text of its answer."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def generate_node(state: SatsangState) -> dict:
    """Answer with the retrieved passages, in the form the mode and intent call for."""
    system = system_prompt(state["mode"], state["intent"])
    messages = _history(state) + [{"role": "user", "content": _rag_prompt(state)}]
    return {"messages": [AIMessage(content=_complete(system, messages, max_tokens=1024))]}


def generate_direct_node(state: SatsangState) -> dict:
    """
    Answer from the conversation alone, without retrieval. Used by Self-inquiry mode,
    which quotes nothing, and by the social and crisis answers of every mode.
    """
    system = system_prompt(state["mode"], state["intent"])
    messages = _history(state) + [{"role": "user", "content": state["messages"][-1].content}]
    return {"messages": [AIMessage(content=_complete(system, messages, max_tokens=512))]}


def decline_node(state: SatsangState) -> dict:
    """Politely redirects off-topic requests back to the teachings."""
    return {"messages": [AIMessage(content=DECLINE_MESSAGE)]}
