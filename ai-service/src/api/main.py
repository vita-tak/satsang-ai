import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from openai import OpenAI
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.agent.graph import build_graph
from src.agent.state import Mode
from src.api.middleware.rate_limit import limiter
from src.api.transcribe import router as transcribe_router
from src.audio.stt.glossary import build_prompt
from src.audio.stt.tokens import load_token_counter
from src.audio.stt.transcriber import Transcriber
from src.config import OPENAI_API_KEY, WHISPER_PROMPT_MAX_TOKENS
from src.rag.retriever import Retriever


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


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = body.session_id or str(uuid.uuid4())
    history = sessions.get(session_id, [])

    try:
        result = graph.invoke({
            "messages": history + [HumanMessage(content=body.message)],
            "mode": body.mode,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    sessions[session_id] = result["messages"]
    return ChatResponse(
        response=result["messages"][-1].content,
        session_id=session_id,
    )