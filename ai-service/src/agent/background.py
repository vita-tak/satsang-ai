"""
Retrieved passages as the model may see them.

The model never sees a chunk's metadata (reference, source, summary, score): only its text, and
that text is scrubbed of what in it still points to a source. Talk headers, page numbers, running
heads, dates, footnote marks and citations are removed; speaker labels become "Question:" and
"Answer:"; the names of the teacher, the editor and the ashram become plain roles. If the model
never sees a reference or a name, it cannot repeat one.
"""
import re
from collections.abc import Iterable

from src.rag.chunk import RetrievedChunk

# The scrub list: the names and titles that occur in the corpus. It is not the private names list
# of the no-names check, which lives only in the tests, and neither list ever goes into a prompt.
TITLES = ("Talks with Sri Ramana Maharshi", "Be As You Are")
NEUTRAL_NAMES = {
    "Sri Ramana Maharshi": "the teacher",
    "Ramana Maharshi": "the teacher",
    "Sri Bhagavan": "the teacher",
    "Sri Ramana": "the teacher",
    "the Maharshi": "the teacher",
    "Bhagavan": "the teacher",
    "Maharshi": "the teacher",
    "Ramana": "the teacher",
    "Sri Ramanasramam": "the ashram",
    "Ramanasramam": "the ashram",
    "David Godman": "the editor",
    "Godman": "the editor",
}

# Entries of the second book's glossary are index lines with page numbers, not definitions.
INDEX_GLOSSARY_REFERENCE = "Be As You Are, Glossary"

_NEUTRAL_BY_NAME = {name.casefold(): role for name, role in NEUTRAL_NAMES.items()}
# Longest first, so a full name is replaced whole and no stray "Sri" is left behind.
_NAME = re.compile(
    r"(?<!\w)(?:"
    + "|".join(re.escape(name) for name in sorted(NEUTRAL_NAMES, key=len, reverse=True))
    + r")(?!\w)",
    re.IGNORECASE,
)
_TITLE = re.compile("|".join(re.escape(title) for title in TITLES), re.IGNORECASE)
_TALK_HEADER = re.compile(r"Talk \d+\.?")
_PAGE_NUMBER = re.compile(r"\d{1,4}")
_DATE = re.compile(r"\d{1,2}(?:st|nd|rd|th) [A-Z][a-z]+,? \d{4}\.?")
_QUESTION_LABEL = re.compile(r"^(?:D\.?|Q)\s*:\s*", re.MULTILINE)
_ANSWER_LABEL = re.compile(
    r"^(?:M\.?|A|Sri Bhagavan|Bhagavan|Maharshi|Sri Ramana)\s*:\s*", re.MULTILINE
)
# A scripture cited with chapter and verse in brackets, such as a book name, II, 48.
_CITATION = re.compile(r"\s*\([^()]{0,40}?\b[IVXLC]+,\s*\d+\.?\)")
# A footnote number glued to the end of a word or to punctuation.
_FOOTNOTE_MARK = re.compile(r"(?<=[a-z.,;:?!'\u2019\"\u201d)\]])\d{1,3}(?=\s|$)")


def background_passages(chunks: Iterable[RetrievedChunk], min_score: float) -> list[str]:
    """
    The scrubbed texts of the chunks that pass the relevance threshold, in the retriever's order.
    An empty list means the context is insufficient.
    """
    texts = (
        scrub(chunk.text)
        for chunk in chunks
        if chunk.score >= min_score and chunk.reference != INDEX_GLOSSARY_REFERENCE
    )
    return [text for text in texts if text]


def copy_sources(chunks: Iterable[RetrievedChunk], min_score: float) -> list[str]:
    """
    The passages a reply must not copy six words from: the background without glossary
    definitions, which are too short to restate without sharing words (the owner's decision
    after round R3).
    """
    return background_passages(
        (chunk for chunk in chunks if chunk.chunk_type != "glossary_entry"), min_score
    )


def scrub(text: str) -> str:
    """A passage's text without anything that still points to a source."""
    text = _without_page_furniture(text)
    text = _CITATION.sub("", text)
    text = _FOOTNOTE_MARK.sub("", text)
    text = _QUESTION_LABEL.sub("Question: ", text)
    text = _ANSWER_LABEL.sub("Answer: ", text)
    text = _TITLE.sub("", text)
    text = _with_neutral_names(text)
    return _tidy(text)


def _without_page_furniture(text: str) -> str:
    """
    Remove the lines that belong to the printed page rather than the text. A page break's blank
    lines go with it, so a sentence it split is joined again.
    """
    kept: list[str] = []
    for line in text.splitlines():
        if _is_page_furniture(line.strip()):
            while kept and not kept[-1].strip():
                kept.pop()
            continue
        kept.append(line)
    return "\n".join(kept)


def _is_page_furniture(line: str) -> bool:
    return (
        _TALK_HEADER.fullmatch(line) is not None
        or _PAGE_NUMBER.fullmatch(line) is not None
        or _DATE.fullmatch(line) is not None
        or _TITLE.fullmatch(line) is not None
        or _is_running_head(line)
    )


def _is_running_head(line: str) -> bool:
    """A chapter or section title in capitals, sometimes followed by its page number."""
    return line.isupper() and " " in line


def _with_neutral_names(text: str) -> str:
    def neutral(match: re.Match[str]) -> str:
        role = _NEUTRAL_BY_NAME[match.group(0).casefold()]
        return role.capitalize() if _starts_sentence(text, match.start()) else role

    return _NAME.sub(neutral, text)


def _starts_sentence(text: str, index: int) -> bool:
    before = text[:index].rstrip(" ")
    return not before or before[-1] in ".?!:\n"


def _tidy(text: str) -> str:
    lines = (" ".join(line.split()) for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
