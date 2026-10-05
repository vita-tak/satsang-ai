from collections.abc import Callable
from typing import TYPE_CHECKING

from src.agent.background import background_passages, copy_sources
from src.agent.state import GuideState
from src.config import CONTEXT_MIN_SCORE

if TYPE_CHECKING:
    # Imported for the annotation only: the real module loads ChromaDB.
    from src.rag.retriever import Retriever


def make_retrieve_node(retriever: "Retriever") -> Callable[[GuideState], dict]:
    """
    Factory that captures the Retriever in a closure so the graph node
    does not need to hold it as part of the LangGraph state.
    """
    def retrieve_node(state: GuideState) -> dict:
        # The classifier's standalone query, so a short reply still finds the right passages
        chunks = retriever.retrieve(state["search_query"])
        return {
            "background": background_passages(chunks, CONTEXT_MIN_SCORE),
            "copy_sources": copy_sources(chunks, CONTEXT_MIN_SCORE),
        }

    return retrieve_node
