import logging

from langgraph.config import get_stream_writer

from src.agent.state import SatsangState
from src.audio.tts.script import plain_script
from src.audio.tts.speaker import Speaker

logger = logging.getLogger(__name__)


def make_tts_node(speaker: Speaker):
    """
    Factory that captures the Speaker, built once at startup, in a closure.

    Each audio chunk is written to the graph's custom stream the moment it arrives, so the caller
    can start playing before the speech is complete. The text answer is already complete when this
    node runs, so a failure here must not cost the seeker the answer: the stream just ends, and
    the caller sends whatever it has. The decline message reaches this node without a script from
    the director and is spoken as it stands.
    """
    def tts_node(state: SatsangState) -> dict:
        script = state.get("voice_script") or plain_script(state["messages"][-1].content)
        write = get_stream_writer()
        try:
            for chunk in speaker.stream(script):
                write(chunk)
        except Exception as error:
            # Only the class is logged: the error text can carry the script
            logger.warning("Speech failed: %s", type(error).__name__)
        return {}

    return tts_node
