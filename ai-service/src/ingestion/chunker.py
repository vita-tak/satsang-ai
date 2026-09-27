import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source: str
    reference: str
    chunk_type: str  # "qa_pair" | "glossary_entry"


TALK_PATTERN = re.compile(r"Talk (\d+)\.")
MAHARSHI_PATTERN = re.compile(r"-\s*(Maharshi|M\.)\s*:")
GLOSSARY_START = re.compile(r"^GLOSSARY", re.MULTILINE)


def chunk_document(text: str) -> list[Chunk]:
    """
    Split the full document text into semantic chunks.

    Talks are split on 'Talk N.' boundaries. Each talk becomes one chunk
    containing the context paragraph and the Maharshi response.
    The glossary section is split into one chunk per term.
    """
    glossary_match = GLOSSARY_START.search(text)

    if glossary_match:
        talks_text = text[:glossary_match.start()]
        glossary_text = text[glossary_match.start():]
    else:
        talks_text = text
        glossary_text = ""

    chunks: list[Chunk] = []
    chunks.extend(_chunk_talks(talks_text))

    if glossary_text:
        chunks.extend(_chunk_glossary(glossary_text))

    return chunks


def _chunk_talks(text: str) -> list[Chunk]:
    """Split text into one chunk per Talk number."""
    splits = TALK_PATTERN.split(text)

    # splits looks like: [preamble, "1", talk_1_body, "2", talk_2_body, ...]
    chunks = []
    i = 1
    while i < len(splits) - 1:
        talk_number = splits[i]
        body = splits[i + 1].strip()

        if body:
            chunks.append(Chunk(
                text=f"Talk {talk_number}.\n\n{body}",
                source="Talks with Sri Ramana Maharshi",
                reference=f"Talk {talk_number}",
                chunk_type="qa_pair",
            ))
        i += 2

    return chunks

def _chunk_glossary(text: str) -> list[Chunk]:
    """Split glossary into one chunk per term definition."""
    chunks = []

    for line in text.splitlines():
        line = line.strip()

        # Skip empty lines, page numbers, and headers
        if not line or line.isdigit() or line in ("GLOSSARY", "Talks with Sri Ramana Maharshi"):
            continue

        # Skip single-letter section headers like "A", "B", etc.
        if re.match(r"^[A-Z]$", line):
            continue

        if ":" in line:
            chunks.append(Chunk(
                text=line,
                source="Talks with Sri Ramana Maharshi",
                reference="Glossary",
                chunk_type="glossary_entry",
            ))

    return chunks