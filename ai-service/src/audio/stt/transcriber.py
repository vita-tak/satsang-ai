from openai import OpenAI

from src.config import WHISPER_MODEL

# The recording formats browsers produce (MediaRecorder) and the extension Whisper needs to
# recognise each one.
AUDIO_EXTENSIONS = {
    "audio/webm": "webm",
    "audio/mp4": "mp4",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/x-m4a": "m4a",
}


class Transcriber:
    """
    Turns a recording into text with Whisper. Instantiate once at startup.

    The recording is sent straight from memory and never written to disk, so there is no file to
    delete afterwards. The prompt holds the Sanskrit terms Whisper would otherwise mishear.
    """

    def __init__(self, client: OpenAI, prompt: str) -> None:
        self._client = client
        self._prompt = prompt

    def transcribe(self, audio: bytes, extension: str) -> str:
        """Return the words spoken in the recording; language is detected automatically."""
        result = self._client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=(f"recording.{extension}", audio),
            prompt=self._prompt,
        )
        return result.text.strip()
