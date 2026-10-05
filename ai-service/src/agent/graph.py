import re
from typing import TYPE_CHECKING

import anthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.agent.crisis_lines import CrisisLine
from src.agent.nodes.classify import make_classify_node
from src.agent.nodes.generate import decline_node, make_generate_node
from src.agent.nodes.retrieve import make_retrieve_node
from src.agent.nodes.tts import make_tts_node
from src.agent.nodes.voice_director import make_voice_director_node
from src.agent.state import GuideReply, GuideState, SatsangState
from src.audio.tts.speaker import Speaker

if TYPE_CHECKING:
    # Imported for the annotation only: the real module loads ChromaDB.
    from src.rag.retriever import Retriever


def route_after_classify(state: GuideState) -> str:
    """
    Choose the branch for a classified message.

    Any risk comes first and goes to the crisis reply, even when the message also looks
    off-topic or social. Off-topic messages get the fixed decline. Only the pointing and
    explanatory registers draw on retrieved passages.
    """
    if state["risk"] != "none":
        return "generate"
    if state["register"] == "off_topic":
        return "decline"
    if state["register"] == "social":
        return "generate"
    return "retrieve"


def build_graph(
    retriever: "Retriever",
    client: anthropic.Anthropic,
    crisis_lines: list[CrisisLine],
    risk_patterns: dict[str, re.Pattern[str]],
) -> CompiledStateGraph:
    """
    Build the guide's graph: one conversation mode, with the register and the risk decided for
    each message.

    Flow:
        classify (risk, register, language, search query; the keyword net may raise the risk)
            any risk                   -> generate (crisis: part 5b only)
            off_topic                  -> decline (fixed sentence, no model call)
            social                     -> generate
            pointing, explanatory      -> retrieve -> generate

    The parts each generation call gets come from the assembly table in prompts.py.
    """
    graph = StateGraph(GuideState)

    graph.add_node("classify", make_classify_node(client, risk_patterns))
    graph.add_node("retrieve", make_retrieve_node(retriever))
    graph.add_node("generate", make_generate_node(client, crisis_lines))
    graph.add_node("decline", decline_node)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {"generate": "generate", "decline": "decline", "retrieve": "retrieve"},
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    graph.add_edge("decline", END)

    return graph.compile()


def guide_reply(state: GuideState) -> GuideReply:
    """The output contract of one run of the guide graph."""
    return GuideReply(
        text=state["messages"][-1].content,
        register=state["register"],
        risk=state["risk"],
        direction=state.get("direction"),
    )


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
