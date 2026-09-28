from src.agent.state import SatsangState
from src.rag.retriever import Retriever


def _label(chunk) -> str:
    """The passage header. Marks the editor's commentary so it is never quoted as Ramana's words."""
    if chunk.chunk_type == "passage":
        return f"{chunk.reference} (editor's commentary)"
    return chunk.reference


def _format_context(chunks) -> str:
    return "\n\n---\n\n".join(f"[{_label(c)}]\n{c.text}" for c in chunks)


def make_retrieve_node(retriever: Retriever):
    """
    Factory that captures the Retriever in a closure so the graph node
    does not need to hold it as part of the LangGraph state.
    """
    def retrieve_node(state: SatsangState) -> dict:
        # The classifier's standalone query, so a short reply still finds the right passages
        chunks = retriever.retrieve(state["search_query"])
        return {"retrieved_context": _format_context(chunks)}

    return retrieve_node
