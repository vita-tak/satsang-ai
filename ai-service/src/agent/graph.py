import anthropic
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from src.agent.state import SatsangState
from src.config import ANTHROPIC_API_KEY, HAIKU_MODEL
from src.rag.retriever import retrieve

SYSTEM_PROMPT = """\
You are a guide in the tradition of Ramana Maharshi, helping seekers with \
the practice of self-inquiry (atma vichara).

You speak with calm authority, grounded in the source texts. When answering, \
draw on the provided passages from "Talks with Sri Ramana Maharshi". \
Quote directly when it illuminates the point.

If the passages do not address the question, say so honestly rather than \
speculating beyond the teachings.

Keep responses concise and contemplative. Avoid spiritual bypassing or \
empty reassurance. Point always toward direct investigation of the Self."""


def _format_context(chunks) -> str:
    """Format retrieved chunks into a single context string for the LLM."""
    sections = []
    for chunk in chunks:
        sections.append(f"[{chunk.reference}]\n{chunk.text}")
    return "\n\n---\n\n".join(sections)


def retrieve_node(state: SatsangState) -> dict:
    """Retrieve relevant passages from ChromaDB based on the latest message."""
    query = state["messages"][-1].content
    chunks = retrieve(query)
    return {"retrieved_context": _format_context(chunks)}


def generate_node(state: SatsangState) -> dict:
    """Generate a response using Claude Haiku with the retrieved context."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_query = state["messages"][-1].content
    context = state["retrieved_context"] or ""

    user_prompt = f"""\
Relevant passages from the teachings:

{context}

---

Seeker's question: {user_query}"""

    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    answer = response.content[0].text
    return {"messages": [AIMessage(content=answer)]}


def build_graph() -> StateGraph:
    """Build and compile the LangGraph agent."""
    graph = StateGraph(SatsangState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()