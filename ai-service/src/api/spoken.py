import logging
from collections.abc import Iterator
from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from src.agent.state import Intent, Mode
from src.audio.tts.script import AudioChunk
from src.config import TTS_AUDIO_FORMAT, TTS_SAMPLE_RATE

logger = logging.getLogger(__name__)


class SpokenAudioFormat(BaseModel):
    """How the client decodes the chunks that follow."""

    mime_type: str
    sample_rate: int


class SpokenTextEvent(BaseModel):
    type: Literal["text"] = "text"
    response: str
    session_id: str
    # None when no sound follows: the speech failed or did not start in time
    audio: SpokenAudioFormat | None


class SpokenAudioEvent(BaseModel):
    type: Literal["audio"] = "audio"
    data: str


class SpokenDoneEvent(BaseModel):
    type: Literal["done"] = "done"


def _line(event: BaseModel) -> str:
    return event.model_dump_json() + "\n"


def _first_chunk(chunks: Iterator[AudioChunk]) -> AudioChunk | None:
    """Wait for the first chunk of audio; None if the speech fails or ends before it comes."""
    try:
        return next(chunks, None)
    except Exception as error:
        # Only the class is logged: the error text can carry the answer
        logger.warning("Speech did not start: %s", type(error).__name__)
        return None


def spoken_events(
    speech_graph: CompiledStateGraph,
    answer: str,
    intent: Intent,
    mode: Mode,
    session_id: str,
) -> Iterator[str]:
    """
    The lines of the streamed response to /chat/spoken: the answer, then its audio.

    The text is held back until the first chunk of audio exists and is sent right before it, so
    the answer and the voice reach the seeker together. The wait is bounded by the speech
    timeouts; if the speech fails, the text goes out alone. Once the text has gone nothing
    can be taken back, so a later failure only ends the stream.
    """
    chunks = speech_graph.stream(
        {"messages": [AIMessage(content=answer)], "intent": intent, "mode": mode},
        stream_mode="custom",
    )
    first = _first_chunk(chunks)
    audio_format = None
    if first is not None:
        audio_format = SpokenAudioFormat(mime_type=TTS_AUDIO_FORMAT, sample_rate=TTS_SAMPLE_RATE)
    yield _line(SpokenTextEvent(response=answer, session_id=session_id, audio=audio_format))

    if first is not None:
        yield _line(SpokenAudioEvent(data=first.data))
        try:
            for chunk in chunks:
                yield _line(SpokenAudioEvent(data=chunk.data))
        except Exception as error:
            logger.warning("Speech stopped early: %s", type(error).__name__)
    yield _line(SpokenDoneEvent())
