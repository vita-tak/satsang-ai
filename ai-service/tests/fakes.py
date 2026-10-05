"""
Test doubles for the guide: a fake Anthropic client that answers from a script or from a
recording of an approved real round, and a retriever that returns synthetic passages.
"""
import hashlib
import json
from collections.abc import Callable
from typing import Any

from anthropic.types import Message
from langchain_core.messages import BaseMessage, HumanMessage

from src.config import HAIKU_MODEL
from src.rag.chunk import RetrievedChunk


class StubRetriever:
    """Returns the same chunks for every query, and keeps the queries it was asked."""

    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.queries: list[str] = []
        self._chunks = chunks

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        self.queries.append(query)
        return list(self._chunks)


class StaleRecording(Exception):
    """A request differs from the one recorded, so the prompt changed after the real round."""


class FakeAnthropic:
    """
    Stands in for anthropic.Anthropic. `messages` is the fake itself, so the nodes' call
    `client.messages.create(...)` lands in `create`, which keeps the request and answers with
    `respond`.
    """

    def __init__(self, respond: Callable[[dict[str, Any]], Message]) -> None:
        self.requests: list[dict[str, Any]] = []
        self.messages = self
        self._respond = respond

    def create(self, **params: Any) -> Message:
        self.requests.append(params)
        return self._respond(params)


def request_sha256(params: dict[str, Any]) -> str:
    """A stable fingerprint of a request, so a replay can tell when the prompt has changed."""
    canonical = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def scripted(*responses: Message) -> FakeAnthropic:
    """A client that answers each request with the next of `responses`."""
    queue = list(responses)
    return FakeAnthropic(lambda params: queue.pop(0))


def replaying(calls: list[dict[str, Any]]) -> FakeAnthropic:
    """A client that answers with the responses of a recorded round, in the recorded order."""
    queue = list(calls)

    def respond(params: dict[str, Any]) -> Message:
        call = queue.pop(0)
        if call["request_sha256"] != request_sha256(params):
            raise StaleRecording("The request differs from the recorded one")
        return Message.model_validate(call["response"])

    return FakeAnthropic(respond)


def guide_state(
    message: str,
    *,
    history: tuple[BaseMessage, ...] = (),
    risk: str = "none",
    register: str = "pointing",
    language: str | None = "en",
    background: list[str] | None = None,
    recent_directions: tuple[str, ...] = (),
    crisis_flagged: bool = False,
) -> dict[str, Any]:
    """The state a generation node receives after classification (and retrieval, if any)."""
    state: dict[str, Any] = {
        "messages": [*history, HumanMessage(message)],
        "risk": risk,
        "register": register,
        "language": language,
        "search_query": message,
        "recent_directions": list(recent_directions),
        "crisis_flagged": crisis_flagged,
    }
    if background is not None:
        state["background"] = background
    return state


# A crisis reply that points to real help, so the crisis path does not write it again.
CRISIS_REPLY = (
    "I read what you wrote, and I am glad you told me. Please contact your local emergency "
    "services or someone you trust now. I am staying here with you."
)


def text_message(text: str) -> Message:
    """A reply as plain text."""
    return _message([{"type": "text", "text": text}], stop_reason="end_turn")


def tool_message(name: str, tool_input: dict[str, Any]) -> Message:
    """A reply as a call of the tool `name`."""
    block = {"type": "tool_use", "id": "toolu_test", "name": name, "input": tool_input}
    return _message([block], stop_reason="tool_use")


def route_message(
    risk: str = "none", register: str = "pointing", language: str = "en", query: str = "the query"
) -> Message:
    """The classifier's decision, as its forced tool call."""
    decision = {"risk": risk, "register": register, "language": language, "search_query": query}
    return tool_message("route_message", decision)


def reply_message(text: str, direction: str = "none") -> Message:
    """A pointing reply, as its forced tool call."""
    return tool_message("reply", {"text": text, "direction": direction})


def _message(content: list[dict[str, Any]], stop_reason: str) -> Message:
    return Message.model_validate({
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": HAIKU_MODEL,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    })
