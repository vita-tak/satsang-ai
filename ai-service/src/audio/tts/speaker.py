from collections.abc import Iterator

from google import genai

from src.audio.tts.script import AudioChunk, VoiceScript
from src.config import (
    TTS_AUDIO_FORMAT,
    TTS_FIRST_CHUNK_TIMEOUT_SECONDS,
    TTS_MODEL,
    TTS_SAMPLE_RATE,
    TTS_VOICE,
)


class SpeechError(Exception):
    """The speech service sent an error, or ended without any audio."""


class Speaker:
    """
    Turns a voice script into streamed audio with Gemini, every answer in the same voice and
    style. Instantiate once at startup.
    """

    def __init__(self, client: genai.Client, style: str) -> None:
        self._client = client
        self._style = style

    def stream(self, script: VoiceScript) -> Iterator[AudioChunk]:
        """
        Yield the script's audio as it is made, in `TTS_AUDIO_FORMAT`.

        The first chunk is what the caller waits for. The request's timeout bounds how long the
        service may stay silent, before the first chunk and between chunks.
        """
        events = self._client.interactions.create(
            model=TTS_MODEL,
            input=[_text_block(script.text, self._style)],
            response_format={
                "type": "audio",
                "mime_type": TTS_AUDIO_FORMAT,
                "sample_rate": TTS_SAMPLE_RATE,
            },
            generation_config={"speech_config": [{"voice": TTS_VOICE}]},
            store=False,
            stream=True,
            timeout=TTS_FIRST_CHUNK_TIMEOUT_SECONDS,
        )
        has_audio = False
        for event in events:
            if event.event_type == "error":
                raise SpeechError("The speech stream reported an error.")
            if event.event_type != "step.delta" or event.delta.type != "audio":
                continue
            if event.delta.data:
                has_audio = True
                yield AudioChunk(data=event.delta.data)
        if not has_audio:
            raise SpeechError("No audio in the speech stream.")


def _text_block(text: str, style: str) -> dict:
    """
    The text as one text block, with the style as a speech annotation over all of it; the
    annotation's indices count bytes, not characters.
    """
    return {
        "type": "text",
        "text": text,
        "annotations": [
            {
                "type": "speech_metadata",
                "style": style,
                "start_index": 0,
                "end_index": len(text.encode("utf-8")),
            }
        ],
    }
