"""
Shared test setup.

pytest imports this file before any test module imports `src`, so the settings below are what
`src.config` reads: fake keys and dead base URLs, so no test can reach a paid API, and a stub in
place of the real retriever module, so ChromaDB is never imported or opened.
"""
import os
import sys
import types

DEAD_URL = "http://127.0.0.1:9"

os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["GOOGLE_API_KEY"] = "test-key"
os.environ["ANTHROPIC_BASE_URL"] = DEAD_URL
os.environ["OPENAI_BASE_URL"] = DEAD_URL
os.environ["GOOGLE_GEMINI_BASE_URL"] = DEAD_URL


class _UnbuildableRetriever:
    """The real Retriever opens ChromaDB, so tests pass a StubRetriever instead."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError("The real Retriever is never built in tests")


_retriever_stub = types.ModuleType("src.rag.retriever")
_retriever_stub.Retriever = _UnbuildableRetriever
sys.modules["src.rag.retriever"] = _retriever_stub
