import logging
import uuid
from contextlib import asynccontextmanager

import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from langchain_core.messages import HumanMessage
from openai import OpenAI
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.agent.graph import build_graph, build_speech_graph
from src.agent.state import Mode
from src.api.middleware.rate_limit import limiter
from src.api.spoken import spoken_events
from src.api.transcribe import router as transcribe_router
from src.audio.stt.glossary import build_prompt
from src.audio.stt.tokens import load_token_counter
from src.audio.stt.transcriber import Transcriber
from src.audio.tts.speaker import Speaker
from src.config import (
    ANTHROPIC_API_KEY,
    CHAT_RATE_LIMIT,
    GOOGLE_API_KEY,
    OPENAI_API_KEY,
    WHISPER_PROMPT_MAX_TOKENS,
)
from src.rag.retriever import Retriever


logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    mode: Mode = "satsang"


class ChatResponse(BaseModel):
    response: str
    session_id: str


graph = None
# In-memory session store: session_id -> list of LangChain messages
sessions: dict[str, list] = {}

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://satsang-ai.vercel.app",
]


def build_transcriber(retriever: Retriever) -> Transcriber:
    """Build the Whisper prompt from the glossary once, so no request has to query the store."""
    prompt = build_prompt(
        retriever.glossary_entries(),
        retriever.text_chunks(),
        load_token_counter(),
        WHISPER_PROMPT_MAX_TOKENS,
    )
    print(f"Transcriber ready: {len(prompt.split(', '))} glossary terms in the Whisper prompt")
    return Transcriber(OpenAI(api_key=OPENAI_API_KEY), prompt)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    retriever = Retriever()
    graph = build_graph(retriever)
    app.state.speech_graph = build_speech_graph(
        anthropic.Anthropic(api_key=ANTHROPIC_API_KEY),
        Speaker(genai.Client(api_key=GOOGLE_API_KEY)),
    )
    app.state.transcriber = build_transcriber(retriever)
    yield


app = FastAPI(title="Satsang AI", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)
app.include_router(transcribe_router)


def answer(body: ChatRequest) -> tuple[str, dict]:
    """
    Run the agent for one message and save the session. Returns the session id and the final
    state. A failure is logged by its class only and reaches the client as a fixed message.
    """
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = body.session_id or str(uuid.uuid4())
    history = sessions.get(session_id, [])

    try:
        result = graph.invoke({
            "messages": history + [HumanMessage(content=body.message)],
            "mode": body.mode,
        })
    except Exception as error:
        # The text of the error can carry keys, file paths, the prompt or the seeker's words
        logger.warning("Agent failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=500, detail="The guide could not answer. Please try again."
        )

    sessions[session_id] = result["messages"]
    return session_id, result


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(CHAT_RATE_LIMIT)
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    session_id, result = answer(body)
    return ChatResponse(response=result["messages"][-1].content, session_id=session_id)


@app.post("/chat/spoken")
@limiter.limit(CHAT_RATE_LIMIT)
def chat_spoken(request: Request, body: ChatRequest) -> StreamingResponse:
    """
    Answer as /chat does, streamed as lines of JSON: the text, then its audio. A plain def,
    since the speech blocks while the audio is made.
    """
    session_id, result = answer(body)
    events = spoken_events(
        request.app.state.speech_graph,
        result["messages"][-1].content,
        result["intent"],
        body.mode,
        session_id,
    )
    return StreamingResponse(events, media_type="application/x-ndjson")
