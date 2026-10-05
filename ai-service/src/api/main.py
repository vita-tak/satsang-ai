import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from langchain_core.messages import BaseMessage, HumanMessage
from openai import OpenAI
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.agent.crisis_lines import load_crisis_lines
from src.agent.graph import build_graph, build_speech_graph, guide_reply
from src.agent.nodes.prompts import VOICE_STYLE
from src.agent.safety_net import load_risk_patterns
from src.agent.state import Direction, GuideReply
from src.agent.voice_adapter import VOICE_MODE, voice_intent
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
    CRISIS_LINES_PATH,
    GOOGLE_API_KEY,
    OPENAI_API_KEY,
    RISK_PHRASES_DIR,
    WHISPER_PROMPT_MAX_TOKENS,
)
from src.rag.retriever import Retriever


logger = logging.getLogger(__name__)


# The guide has one mode. A client that still sends the old `mode` field is not refused: Pydantic
# ignores fields a model does not declare.
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@dataclass
class Session:
    """
    One conversation, kept in memory only: its messages, the directions of its last two pointing
    turns, and whether a crisis was flagged in it. The flag is a boolean and nothing else.
    """

    messages: list[BaseMessage] = field(default_factory=list)
    recent_directions: list[Direction] = field(default_factory=list)
    crisis_flagged: bool = False


graph = None
# In-memory session store: session_id -> Session
sessions: dict[str, Session] = {}

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
    graph = build_graph(
        retriever,
        anthropic.Anthropic(api_key=ANTHROPIC_API_KEY),
        load_crisis_lines(CRISIS_LINES_PATH),
        load_risk_patterns(RISK_PHRASES_DIR),
    )
    app.state.speech_graph = build_speech_graph(
        anthropic.Anthropic(api_key=ANTHROPIC_API_KEY),
        Speaker(genai.Client(api_key=GOOGLE_API_KEY), VOICE_STYLE),
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


def answer(body: ChatRequest) -> tuple[str, GuideReply]:
    """
    Run the guide for one message and save the session. Returns the session id and the reply.
    A failure is logged by its class only and reaches the client as a fixed message.
    """
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = body.session_id or str(uuid.uuid4())
    session = sessions.get(session_id, Session())

    try:
        # LangGraph applies no defaults, so every key the graph reads is passed
        result = graph.invoke({
            "messages": session.messages + [HumanMessage(content=body.message)],
            "recent_directions": session.recent_directions,
            "crisis_flagged": session.crisis_flagged,
        })
    except Exception as error:
        # The text of the error can carry keys, file paths, the prompt or the seeker's words
        logger.warning("Agent failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=500, detail="The guide could not answer. Please try again."
        )

    sessions[session_id] = Session(
        messages=result["messages"],
        recent_directions=result["recent_directions"],
        crisis_flagged=result["crisis_flagged"],
    )
    return session_id, guide_reply(result)


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(CHAT_RATE_LIMIT)
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    session_id, reply = answer(body)
    return ChatResponse(response=reply.text, session_id=session_id)


@app.post("/chat/spoken")
@limiter.limit(CHAT_RATE_LIMIT)
def chat_spoken(request: Request, body: ChatRequest) -> StreamingResponse:
    """
    Answer as /chat does, streamed as lines of JSON: the text, then its audio. A plain def,
    since the speech blocks while the audio is made.
    """
    session_id, reply = answer(body)
    events = spoken_events(
        request.app.state.speech_graph,
        reply.text,
        voice_intent(reply),
        VOICE_MODE,
        session_id,
    )
    return StreamingResponse(events, media_type="application/x-ndjson")
