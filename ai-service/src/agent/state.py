from dataclasses import dataclass
from typing import Literal, Optional
from langgraph.graph import MessagesState

from src.audio.tts.script import VoiceScript

# The voice director still reads the old mode and intent. Until the audio step re-keys it, they
# exist only for the speech graph, filled in by src/agent/voice_adapter.py.
Mode = Literal["satsang", "teachings", "ramana", "self_inquiry"]
Intent = Literal["teaching", "practice", "struggle", "definition", "social", "crisis", "off_topic"]

# How the guide meets a message, chosen per message by the classifier. off_topic is not a voice:
# it marks the fixed decline.
Register = Literal["pointing", "explanatory", "social", "off_topic"]

# unsure takes the crisis path too: a message the classifier hesitates over is treated with care.
Risk = Literal["none", "unsure", "crisis"]

# The six directions of a pointing turn, named as in part 2a of the guide prompt.
Direction = Literal["Who", "Where", "Before or after", "Qualities", "Change", "Leave alone"]

# The rows of the assembly table: the parts a generation call is given.
Situation = Literal["pointing", "explanatory", "social", "crisis"]


@dataclass(frozen=True)
class GuideReply:
    """
    What the guide's text flow hands its callers for one message. A risk other than none means
    the crisis instructions wrote the reply, whatever the register.
    """

    text: str
    register: Register
    risk: Risk
    direction: Direction | None = None


class GuideState(MessagesState):
    """
    State of the guide graph for one message.

    main.py passes the session's recent_directions and crisis_flagged with the messages. The
    classifier writes risk, register, language and search_query; retrieval writes background
    (pointing and explanatory only; empty means the context is insufficient) and copy_sources
    (the passages the copy check compares a reply with); generation writes the reply, its
    direction and the updated recent_directions and crisis_flagged. LangGraph does not apply
    defaults, so a key that may be absent is read with .get().
    """

    recent_directions: list[Direction]
    crisis_flagged: bool
    risk: Risk
    register: Register
    language: str
    search_query: str
    background: list[str]
    copy_sources: list[str]
    direction: Direction | None


class SatsangState(MessagesState):
    """
    State of the speech graph, which still speaks in terms of the old intent and mode.

    Inherits messages (conversation history) from MessagesState.
    LangGraph does not apply the defaults below at runtime, so callers always pass mode.
    """
    retrieved_context: Optional[str] = None
    intent: Optional[Intent] = None
    search_query: Optional[str] = None
    mode: Mode = "satsang"
    voice_script: Optional[VoiceScript] = None
