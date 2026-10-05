"""
Temporary bridge from the guide's output contract to the speech graph.

The voice director still picks its pause note by the old intent, and its input names the old
mode. This module is the only place that knows both worlds. When the audio step keys the voice
director by register, it goes.
"""
from src.agent.state import GuideReply, Intent, Mode

VOICE_MODE: Mode = "satsang"

# The old intent whose voice note is closest to each register: a pointing reply invites the
# person to look (the practice note), an explanatory reply explains (the teaching note). The
# decline keeps off_topic, which the speech graph speaks as it stands.
_INTENT_FOR_REGISTER: dict[str, Intent] = {
    "pointing": "practice",
    "explanatory": "teaching",
    "social": "social",
    "off_topic": "off_topic",
}


def voice_intent(reply: GuideReply) -> Intent:
    """The old intent for the voice director. Any risk means the crisis reply's note."""
    if reply.risk != "none":
        return "crisis"
    return _INTENT_FOR_REGISTER[reply.register]
