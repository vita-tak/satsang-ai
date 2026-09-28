import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.agent.graph import build_graph
from src.agent.state import Mode
from src.api.middleware.rate_limit import limiter
from src.rag.retriever import Retriever


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    mode: Mode = "teachings"


class ChatResponse(BaseModel):
    response: str
    session_id: str


graph = None
# In-memory session store: session_id -> list of LangChain messages
sessions: dict[str, list] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    retriever = Retriever()
    graph = build_graph(retriever)
    yield


app = FastAPI(title="Satsang AI", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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