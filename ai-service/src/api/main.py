import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from src.agent.graph import build_graph
from src.rag.retriever import Retriever


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = request.session_id or str(uuid.uuid4())
    history = sessions.get(session_id, [])

    try:
        result = graph.invoke({
            "messages": history + [HumanMessage(content=request.message)]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    sessions[session_id] = result["messages"]
    return ChatResponse(
        response=result["messages"][-1].content,
        session_id=session_id,
    )