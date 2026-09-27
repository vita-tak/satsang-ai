from dataclasses import dataclass

import chromadb
from openai import OpenAI
from sentence_transformers import CrossEncoder

from src.config import (
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    RERANK_CANDIDATES,
    TOP_K,
)

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-TinyBERT-L-2-v2"


@dataclass
class RetrievedChunk:
    text: str
    reference: str
    chunk_type: str
    summary: str
    score: float


def _embed_query(client: OpenAI, query: str) -> list[float]:
    """Embed a query string with text-embedding-3-small."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query],
    )
    return response.data[0].embedding


def _rerank(
    query: str,
    candidates: list[dict],
    top_k: int,
) -> list[RetrievedChunk]:
    """
    Re-rank candidate chunks with a CrossEncoder and return the top_k best.

    The CrossEncoder reads query and chunk together (not as separate vectors)
    and produces a more precise relevance score than embedding similarity alone.
    """
    encoder = CrossEncoder(CROSS_ENCODER_MODEL)
    pairs = [[query, c["document"]] for c in candidates]
    scores = encoder.predict(pairs)

    ranked = sorted(
        zip(scores, candidates),
        key=lambda x: x[0],
        reverse=True,
    )

    return [
        RetrievedChunk(
            text=c["document"],
            reference=c["metadata"]["reference"],
            chunk_type=c["metadata"]["chunk_type"],
            summary=c["metadata"]["summary"],
            score=float(score),
        )
        for score, c in ranked[:top_k]
    ]


def retrieve(
    query: str,
    top_k: int = TOP_K,
    candidates: int = RERANK_CANDIDATES,
) -> list[RetrievedChunk]:
    """
    Retrieve the most relevant chunks for a query.

    Steps:
    1. Embed the query with text-embedding-3-small
    2. Fetch the top candidates from ChromaDB by vector similarity
    3. Re-rank with CrossEncoder and return the top_k best

    """
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = chroma_client.get_collection(name=COLLECTION_NAME)

    query_embedding = _embed_query(openai_client, query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidates,
        include=["documents", "metadatas", "distances"],
    )

    candidate_chunks = [
        {"document": doc, "metadata": meta}
        for doc, meta in zip(
            results["documents"][0],
            results["metadatas"][0],
        )
    ]

    return _rerank(query, candidate_chunks, top_k)