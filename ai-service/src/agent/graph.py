from langgraph.graph import StateGraph, START, END

from src.agent.state import SatsangState
from src.agent.nodes.classify import classify_intent_node
from src.agent.nodes.retrieve import make_retrieve_node
from src.agent.nodes.generate import (
    make_generate_node,
    guided_inquiry_node,
    decline_node,
    SATSANG_SYSTEM,
    PERSONAL_STRUGGLE_SYSTEM,
)
from src.rag.retriever import Retriever


def build_graph(retriever: Retriever):
    """
    Build the LangGraph agent with intent-based routing.

    Flow:
        classify_intent
            satsang / definition / personal_struggle -> retrieve -> generate / generate_soft
            self_inquiry                             -> guided_inquiry
            off_topic                                -> decline
    """
    graph = StateGraph(SatsangState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("retrieve", make_retrieve_node(retriever))
    graph.add_node("generate", make_generate_node(SATSANG_SYSTEM))
    graph.add_node("generate_soft", make_generate_node(PERSONAL_STRUGGLE_SYSTEM))
    graph.add_node("guided_inquiry", guided_inquiry_node)
    graph.add_node("decline", decline_node)

    graph.add_edge(START, "classify_intent")

    # Route to the correct branch based on classified intent
    graph.add_conditional_edges(
        "classify_intent",
        lambda s: s["intent"],
        {
            "satsang": "retrieve",
            "definition": "retrieve",
            "personal_struggle": "retrieve",
            "self_inquiry": "guided_inquiry",
            "off_topic": "decline",
        },
    )

    # After retrieval, personal_struggle gets a softer generation prompt
    graph.add_conditional_edges(
        "retrieve",
        lambda s: "generate_soft" if s["intent"] == "personal_struggle" else "generate",
        {"generate": "generate", "generate_soft": "generate_soft"},
    )

    graph.add_edge("generate", END)
    graph.add_edge("generate_soft", END)
    graph.add_edge("guided_inquiry", END)
    graph.add_edge("decline", END)

    return graph.compile()