from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import anthropic
from pydantic import BaseModel

from src.config import ANTHROPIC_API_KEY, HAIKU_MODEL
from src.ingestion.chunker import Chunk

SYSTEM_PROMPT = (
    "You are a metadata generator for passages from spiritual texts on self-inquiry."
)

QA_PAIR_PROMPT = """\
Analyze this passage from a spiritual text on self-inquiry and generate metadata for it.

Reference: {reference}

Passage:
{text}"""

PASSAGE_PROMPT = """\
Analyze this introductory passage from a spiritual text on self-inquiry and generate metadata for it.

Reference: {reference}

Passage:
{text}"""

GLOSSARY_PROMPT = """\
Analyze this glossary entry from a spiritual text on self-inquiry and generate metadata for it.

Reference: {reference}

Entry:
{text}"""

QA_TOOL = {
    "name": "generate_metadata",
    "description": "Generate metadata for a passage or Q&A from a spiritual text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "One sentence describing what this passage is about.",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-6 specific terms or phrases central to this passage.",
            },
            "topic_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 broader thematic categories, e.g. 'self-inquiry', 'the mind', 'liberation'.",
            },
            "hypothetical_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 questions a seeker might ask that this passage answers.",
            },
        },
        "required": ["summary", "keywords", "topic_tags", "hypothetical_questions"],
    },
}

GLOSSARY_TOOL = {
    "name": "generate_metadata",
    "description": "Generate metadata for a glossary entry from a spiritual text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "One sentence describing what this term means.",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 terms related to this entry.",
            },
            "topic_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-3 thematic categories this term belongs to.",
            },
        },
        "required": ["summary", "keywords", "topic_tags"],
    },
}


class EnrichedChunk(BaseModel):
    text: str
    source: str
    reference: str
    chunk_type: str
    summary: str
    keywords: list[str]
    topic_tags: list[str]
    hypothetical_questions: Optional[list[str]] = None


def _build_request(chunk: Chunk) -> tuple[str, list]:
    if chunk.chunk_type == "qa_pair":
        prompt = QA_PAIR_PROMPT.format(reference=chunk.reference, text=chunk.text)
        tool = QA_TOOL
    elif chunk.chunk_type == "passage":
        prompt = PASSAGE_PROMPT.format(reference=chunk.reference, text=chunk.text)
        tool = QA_TOOL
    else:
        prompt = GLOSSARY_PROMPT.format(reference=chunk.reference, text=chunk.text)
        tool = GLOSSARY_TOOL
    return prompt, [tool]


def generate_metadata_for_chunk(
    client: anthropic.Anthropic,
    chunk: Chunk,
) -> EnrichedChunk:
    prompt, tools = _build_request(chunk)

    message = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        tools=tools,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_use = next(b for b in message.content if b.type == "tool_use")
    data = tool_use.input

    return EnrichedChunk(
        text=chunk.text,
        source=chunk.source,
        reference=chunk.reference,
        chunk_type=chunk.chunk_type,
        summary=data["summary"],
        keywords=data["keywords"],
        topic_tags=data["topic_tags"],
        hypothetical_questions=data.get("hypothetical_questions"),
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