"""
The keyword safety net: a check on the person's message that does not depend on the classifier.

Each language has a phrase list in guide/risk_phrases/<code>.txt, one phrase per line, with # for
comments. The detected language picks the list, English when there is none for it. A match
raises the risk to crisis whatever the classifier said; the net never lowers a risk. Matching
ignores case and apostrophes and needs whole words, so "don't" also matches "dont".
"""
import re
from pathlib import Path

from src.config import FALLBACK_LANGUAGE


def load_risk_patterns(directory: Path) -> dict[str, re.Pattern[str]]:
    """One pattern per language code (the file name), matching any phrase of that list."""
    patterns = {
        path.stem: _any_phrase(_read_phrases(path)) for path in sorted(directory.glob("*.txt"))
    }
    if FALLBACK_LANGUAGE not in patterns:
        raise ValueError(f"The risk phrases need a {FALLBACK_LANGUAGE}.txt list")
    return patterns


def mentions_risk(
    message: str, language: str | None, patterns: dict[str, re.Pattern[str]]
) -> bool:
    """Whether the message contains a phrase from the list for its language."""
    pattern = patterns.get(language or FALLBACK_LANGUAGE, patterns[FALLBACK_LANGUAGE])
    return pattern.search(_normalize(message)) is not None


def _read_phrases(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [_normalize(line) for line in lines if line and not line.startswith("#")]


def _any_phrase(phrases: list[str]) -> re.Pattern[str]:
    longest_first = sorted(phrases, key=len, reverse=True)
    alternatives = "|".join(re.escape(phrase) for phrase in longest_first)
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)")


def _normalize(text: str) -> str:
    """Lowercase, without apostrophes, with single spaces."""
    return " ".join(re.sub(r"['\u2019]", "", text.lower()).split())
