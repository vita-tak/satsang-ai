import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from openai import OpenAIError
from pydantic import BaseModel

from src.api.middleware.rate_limit import limiter
from src.audio.stt.transcriber import AUDIO_EXTENSIONS, Transcriber
from src.config import TRANSCRIBE_MAX_BYTES, TRANSCRIBE_RATE_LIMIT

logger = logging.getLogger(__name__)
router = APIRouter()


class TranscribeResponse(BaseModel):
    text: str


def get_transcriber(request: Request) -> Transcriber:
    return request.app.state.transcriber


TranscriberDep = Annotated[Transcriber, Depends(get_transcriber)]


def _audio_extension(audio: UploadFile) -> str:
    """The file extension for the upload's type; the codec list after ';' is ignored."""
    content_type = (audio.content_type or "").split(";")[0].strip().lower()
    extension = AUDIO_EXTENSIONS.get(content_type)
    if extension is None:
        raise HTTPException(status_code=415, detail="Unsupported audio format.")
    return extension


def _read_audio(audio: UploadFile) -> bytes:
    """Read the whole upload, then close it so the server keeps nothing of the recording."""
    try:
        data = audio.file.read(TRANSCRIBE_MAX_BYTES + 1)
    finally:
        audio.file.close()
    if not data:
        raise HTTPException(status_code=400, detail="The recording is empty.")
    if len(data) > TRANSCRIBE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="The recording is too long.")
    return data


@router.post("/transcribe")
@limiter.limit(TRANSCRIBE_RATE_LIMIT)
def transcribe(
    request: Request,
    audio: UploadFile,
    transcriber: TranscriberDep,
) -> TranscribeResponse:
    extension = _audio_extension(audio)
    data = _read_audio(audio)

    try:
        text = transcriber.transcribe(data, extension)
    except OpenAIError as error:
        # Only the error's class is logged, and the client gets a fixed message: the text of the
        # error can carry request details
        logger.warning("Transcription failed: %s", type(error).__name__)
        raise HTTPException(status_code=502, detail="Transcription failed.")
    return TranscribeResponse(text=text)
