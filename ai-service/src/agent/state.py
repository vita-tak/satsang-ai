from typing import Literal, Optional
from langgraph.graph import MessagesState

# How the guide answers, chosen by the seeker. The mode never influences classification.
Mode = Literal["satsang", "teachings", "ramana", "self_inquiry"]

# What the seeker's message is doing, as classified in context.
Intent = Literal["teaching", "practice", "struggle", "definition", "social", "crisis", "off_topic"]


class SatsangState(MessagesState):
    """
    State object that flows through the LangGraph agent.

    Inherits messages (conversation history) from MessagesState.
    LangGraph does not apply the defaults below at runtime, so main.py always passes mode.
    """
    retrieved_context: Optional[str] = None
    intent: Optional[Intent] = None
    search_query: Optional[str] = None
    mode: Mode = "satsang"
