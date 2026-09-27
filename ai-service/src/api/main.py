from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from src.agent.graph import build_graph


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    graph = build_graph()
    yield


app = FastAPI(title="Satsang AI", lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        result = graph.invoke({
            "messages": [HumanMessage(content=request.message)]
        })
        return ChatResponse(response=result["messages"][-1].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")