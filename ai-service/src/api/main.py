from contextlib import asynccontextmanager

from fastapi import FastAPI
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
    result = graph.invoke({
        "messages": [HumanMessage(content=request.message)]
    })
    return ChatResponse(response=result["messages"][-1].content)