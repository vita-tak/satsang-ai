import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import anthropic
from pydantic import BaseModel

from src.config import ANTHROPIC_API_KEY, HAIKU_MODEL
from src.ingestion.chunker import Chunk

QA_PAIR_SYSTEM = (
    "You are a metadata generator for passages from spiritual texts on self-inquiry. "
    "You return only valid JSON with no explanation or markdown."
)

GLOSSARY_SYSTEM = (
    "You are a metadata generator for glossary entries from spiritual texts on self-inquiry. "
    "You return only valid JSON with no explanation or markdown."
)

QA_PAIR_PROMPT = """\
Analyze this passage from "Talks with Sri Ramana Maharshi" and return a JSON object \
with exactly these fields:

- summary: one sentence describing what this passage is about
- keywords: list of 3-6 specific terms or phrases central to this passage
- topic_tags: list of 2-4 broader thematic categories (e.g. "self-inquiry", "the mind", "liberation")
- hypothetical_questions: list of 2-4 questions a seeker might ask that this passage answers

Reference: {reference}

Passage:
{text}"""

GLOSSARY_PROMPT = """\
Analyze this glossary entry from "Talks with Sri Ramana Maharshi" and return a JSON object \
with exactly these fields:

- summary: one sentence describing what this term means
- keywords: list of 2-4 terms related to this entry
- topic_tags: list of 1-3 thematic categories this term belongs to

Reference: {reference}

Entry:
{text}"""


class ChunkMetadata(BaseModel):
    summary: str
    keywords: list[str]
    topic_tags: list[str]
    hypothetical_questions: Optional[list[str]] = None


class EnrichedChunk(BaseModel):
    text: str
    source: str
    reference: str
    chunk_type: str
    summary: str
    keywords: list[str]
    topic_tags: list[str]
    hypothetical_questions: Optional[list[str]] = None


def _build_prompt(chunk: Chunk) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given chunk type."""
    if chunk.chunk_type == "qa_pair":
        return QA_PAIR_SYSTEM, QA_PAIR_PROMPT.format(
            reference=chunk.reference,
            text=chunk.text,
        )
    return GLOSSARY_SYSTEM, GLOSSARY_PROMPT.format(
        reference=chunk.reference,
        text=chunk.text,
    )


def _parse_metadata(raw: str, chunk_type: str) -> ChunkMetadata:
    """Parse and validate the JSON response from the model."""
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    if chunk_type != "qa_pair":
        data.pop("hypothetical_questions", None)
    return ChunkMetadata(**data)


def generate_metadata_for_chunk(
    client: anthropic.Anthropic,
    chunk: Chunk,
) -> EnrichedChunk:
    """Call Claude Haiku and return the chunk enriched with precomputed metadata."""
    system_prompt, user_prompt = _build_prompt(chunk)

    message = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    metadata = _parse_metadata(raw, chunk.chunk_type)

    return EnrichedChunk(
        text=chunk.text,
        source=chunk.source,
        reference=chunk.reference,
        chunk_type=chunk.chunk_type,
        summary=metadata.summary,
        keywords=metadata.keywords,
        topic_tags=metadata.topic_tags,
        hypothetical_questions=metadata.hypothetical_questions,
    )


def generate_metadata(
    chunks: list[Chunk],
    limit: Optional[int] = None,
    max_workers: int = 20,
) -> list[EnrichedChunk]:
    """
    Generate precomputed metadata for a list of chunks in parallel.

    Args:
        chunks: list of Chunk objects from the chunker
        limit: if set, process only the first N chunks (useful for test runs)
        max_workers: number of concurrent API calls

    Returns:
        list of EnrichedChunk objects with metadata attached, in original order
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    target = chunks[:limit] if limit else chunks
    total = len(target)
    results: dict[int, EnrichedChunk] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(generate_metadata_for_chunk, client, chunk): i
            for i, chunk in enumerate(target)
        }
        for future in as_completed(futures):
            i = futures[future]
            chunk = target[i]
            try:
                results[i] = future.result()
                print(f"[{len(results)}/{total}] {chunk.reference}")
            except Exception as e:
                print(f"  Error on {chunk.reference}: {e}")

    return [results[i] for i in range(total) if i in results]