from src.agent.state import SatsangState
from src.rag.retriever import Retriever


def _format_context(chunks) -> str:
    return "\n\n---\n\n".join(f"[{c.reference}]\n{c.text}" for c in chunks)


def make_retrieve_node(retriever: Retriever):
    """
    Factory that captures the Retriever in a closure so the graph node
    does not need to hold it as part of the LangGraph state.
    """
    def retrieve_node(state: SatsangState) -> dict:
        query = state["messages"][-1].content
        chunks = retriever.retrieve(query)
        return {"retrieved_context": _format_context(chunks)}

    return retrieve_node