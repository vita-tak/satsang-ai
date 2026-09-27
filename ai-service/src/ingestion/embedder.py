import hashlib
import os
from typing import Optional

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from src.ingestion.metadata_generator import EnrichedChunk

load_dotenv(".env.local")

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "satsang"


def _chunk_id(chunk: EnrichedChunk, index: int) -> str:
    """
    Generate a stable, unique ID for a chunk.

    Uses a hash of source + reference + index so re-running ingestion
    upserts existing documents rather than creating duplicates.
    """
    raw = f"{chunk.source}::{chunk.reference}::{index}"
    return hashlib.md5(raw.encode()).hexdigest()


def _embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of texts with OpenAI text-embedding-3-small.

    Sends all texts in a single API call for efficiency.
    """
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def _build_metadata(chunk: EnrichedChunk) -> dict:
    """
    Build the ChromaDB metadata dict for a chunk.

    ChromaDB metadata values must be str, int, float, or bool.
    Lists are serialized as comma-separated strings for filtering.
    """
    metadata: dict = {
        "source": chunk.source,
        "reference": chunk.reference,
        "chunk_type": chunk.chunk_type,
        "summary": chunk.summary,
        "keywords": ", ".join(chunk.keywords),
        "topic_tags": ", ".join(chunk.topic_tags),
    }
    if chunk.hypothetical_questions:
        metadata["hypothetical_questions"] = " | ".join(chunk.hypothetical_questions)
    return metadata


def store_chunks(
    chunks: list[EnrichedChunk],
    persist_dir: Optional[str] = None,
    batch_size: int = 100,
) -> chromadb.Collection:
    """
    Embed and store a list of EnrichedChunks in ChromaDB.

    Args:
        chunks: enriched chunks with precomputed metadata
        persist_dir: path to ChromaDB storage directory (defaults to env var)
        batch_size: number of chunks to embed and insert per API call

    Returns:
        the ChromaDB collection after insertion
    """
    if persist_dir is None:
        persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma")

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    total = len(chunks)
    for start in range(0, total, batch_size):
        batch = chunks[start : start + batch_size]
        end = min(start + batch_size, total)
        print(f"Embedding batch {start + 1}-{end} / {total}")

        texts = [c.text for c in batch]
        embeddings = _embed_texts(openai_client, texts)

        collection.upsert(
            ids=[_chunk_id(c, start + i) for i, c in enumerate(batch)],
            embeddings=embeddings,
            documents=texts,
            metadatas=[_build_metadata(c) for c in batch],
        )

    print(f"Stored {total} chunks in collection '{COLLECTION_NAME}' at {persist_dir}")
    return collection