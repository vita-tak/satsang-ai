import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    reference: str
    chunk_type: str  # "qa_pair" | "glossary_entry" | "passage"


# Talks with Sri Ramana Maharshi
TALK_PATTERN = re.compile(r"Talk (\d+)\.")
GLOSSARY_START = re.compile(r"^GLOSSARY", re.MULTILINE)

# Be As You Are
BAYA_CHAPTER_RE = re.compile(r"^CHAPTER\s+(\d+)\s*$", re.MULTILINE)


def chunk_document(text: str) -> list[Chunk]:
    """
    Split Talks with Sri Ramana Maharshi into chunks.

    Talks are split on 'Talk N.' boundaries. The glossary section
    is split into one chunk per term.
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

        if not line or line.isdigit() or line in ("GLOSSARY", "Talks with Sri Ramana Maharshi"):
            continue

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


def chunk_baya(main_text: str, glossary_text: str) -> list[Chunk]:
    """
    Split Be As You Are into chunks.

    Main text is split per chapter into passage and qa_pair chunks.
    Glossary text is split into glossary_entry chunks.
    """
    chunks: list[Chunk] = []
    chunks.extend(_chunk_baya_chapters(main_text))
    chunks.extend(_chunk_baya_glossary(glossary_text))
    return chunks


def _chunk_baya_chapters(text: str) -> list[Chunk]:
    """Split main text into chunks per chapter."""
    matches = list(BAYA_CHAPTER_RE.finditer(text))
    chunks = []

    for i, match in enumerate(matches):
        chapter_num = int(match.group(1))

        after_heading = text[match.end():].lstrip("\n")
        title_end = after_heading.index("\n")
        chapter_title = after_heading[:title_end].strip()

        content_start = match.end() + title_end + 1
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapter_text = text[content_start:content_end].strip()

        reference = f"Be As You Are, Ch. {chapter_num}: {chapter_title}"
        chunks.extend(_parse_chapter_chunks(chapter_text, reference))

    return chunks


def _parse_chapter_chunks(text: str, reference: str) -> list[Chunk]:
    """
    Parse a chapter into passage and qa_pair chunks.

    Prose before the first Q: becomes a passage chunk.
    Each Q/A block becomes a qa_pair chunk.
    """
    source = "Be As You Are"
    chunks = []
    lines = text.split("\n")

    current_passage: list[str] = []
    current_qa: list[str] = []
    in_qa = False

    def flush_passage() -> None:
        t = "\n".join(current_passage).strip()
        if t:
            chunks.append(Chunk(text=t, source=source, reference=reference, chunk_type="passage"))
        current_passage.clear()

    def flush_qa() -> None:
        t = "\n".join(current_qa).strip()
        if t:
            chunks.append(Chunk(text=t, source=source, reference=reference, chunk_type="qa_pair"))
        current_qa.clear()

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Q:"):
            if in_qa:
                flush_qa()
            else:
                flush_passage()
            in_qa = True
            current_qa.append(stripped)

        elif in_qa:
            current_qa.append(stripped)

        else:
            current_passage.append(stripped)

    if in_qa:
        flush_qa()
    else:
        flush_passage()

    return chunks


def _chunk_baya_glossary(text: str) -> list[Chunk]:
    """Split glossary into one chunk per term."""
    chunks = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lower() == "glossary" or line.isdigit():
            i += 1
            continue
        if i + 1 < len(lines) and len(line) < 40 and not line.endswith("."):
            definition = lines[i + 1]
            chunks.append(Chunk(
                text=f"{line}\n{definition}",
                source="Be As You Are",
                reference="Be As You Are, Glossary",
                chunk_type="glossary_entry",
            ))
            i += 2
        else:
            i += 1

    return chunks