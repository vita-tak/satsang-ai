from langgraph.graph import StateGraph, START, END

from src.agent.state import SatsangState
from src.agent.nodes.classify import classify_intent_node
from src.agent.nodes.retrieve import make_retrieve_node
from src.agent.nodes.generate import generate_node, generate_direct_node, decline_node
from src.rag.retriever import Retriever


def route_after_classify(state: SatsangState) -> str:
    """
    Choose the branch for a classified message.

    Off-topic messages are declined. Social and crisis answers need no passages in any mode,
    and neither does Self-inquiry mode, which quotes nothing; definitions always look up
    the texts. Everything else is answered from retrieved passages.
    """
    intent = state["intent"]
    if intent == "off_topic":
        return "decline"
    if intent in ("social", "crisis"):
        return "generate_direct"
    if state["mode"] == "self_inquiry" and intent != "definition":
        return "generate_direct"
    return "retrieve"


def build_graph(retriever: Retriever):
    """
    Build the LangGraph agent with intent- and mode-based routing.

    Flow:
        classify_intent (sees the guide's previous reply, writes a search query)
            off_topic                                        -> decline
            social, crisis                                   -> generate_direct
            teaching / practice / struggle in self_inquiry   -> generate_direct
            everything else, and definition in every mode    -> retrieve -> generate

    The system prompt for each answer comes from prompts.system_prompt(mode, intent).
    """
    graph = StateGraph(SatsangState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("retrieve", make_retrieve_node(retriever))
    graph.add_node("generate", generate_node)
    graph.add_node("generate_direct", generate_direct_node)
    graph.add_node("decline", decline_node)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "decline": "decline",
            "generate_direct": "generate_direct",
            "retrieve": "retrieve",
        },
    )
    graph.add_edge("retrieve", "generate")

    graph.add_edge("generate", END)
    graph.add_edge("generate_direct", END)
    graph.add_edge("decline", END)

    return graph.compile()
