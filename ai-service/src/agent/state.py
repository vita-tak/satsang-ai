from typing import Optional
from langgraph.graph import MessagesState


class SatsangState(MessagesState):
    """
    State object that flows through the LangGraph agent.

    Inherits messages (conversation history) from MessagesState.
    """
    retrieved_context: Optional[str] = None