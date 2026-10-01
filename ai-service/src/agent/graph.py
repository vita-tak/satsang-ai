import anthropic
from langgraph.graph import StateGraph, START, END

from src.agent.state import SatsangState
from src.agent.nodes.classify import classify_intent_node
from src.agent.nodes.retrieve import make_retrieve_node
from src.agent.nodes.generate import generate_node, generate_direct_node, decline_node
from src.agent.nodes.tts import make_tts_node
from src.agent.nodes.voice_director import make_voice_director_node
from src.audio.tts.speaker import Speaker
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


def route_speech(state: SatsangState) -> str:
    """The fixed decline message is spoken as it stands, so it skips the voice director."""
    return "tts" if state["intent"] == "off_topic" else "voice_director"


def build_speech_graph(anthropic_client: anthropic.Anthropic, speaker: Speaker):
    """
    Build the graph that speaks an answer that was already delivered as text.

    It runs after /chat, from /speak, so the seeker reads the text at once and the audio
    follows; speaking takes seconds and the text should not wait for it.

    Flow:
        off_topic (the fixed decline message)  -> tts
        every other intent                     -> voice_director -> tts
    """
    graph = StateGraph(SatsangState)

    graph.add_node("voice_director", make_voice_director_node(anthropic_client))
    graph.add_node("tts", make_tts_node(speaker))

    graph.add_conditional_edges(
        START, route_speech, {"voice_director": "voice_director", "tts": "tts"}
    )
    graph.add_edge("voice_director", "tts")
    graph.add_edge("tts", END)

    return graph.compile()
