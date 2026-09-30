import re
from collections import Counter
from collections.abc import Callable, Iterable

# A glossary term is a short run of letters: no digits, no sentence. Longer heads are book titles
# from the Talks glossary's list of further reading.
TERM_PATTERN = re.compile(r"^[^\W\d_]+(?:[- ][^\W\d_]+){0,2}$")
MIN_TERM_LENGTH = 3
PARENTHETICAL = re.compile(r"\s*\([^)]*\)")
NON_WORD = re.compile(r"[^\w-]+")


def extract_term(entry: str) -> str | None:
    """
    Return the Sanskrit term an entry defines, lowercased, or None when the entry is not a term.

    The Talks glossary is one line per term, "term: definition". The Be As You Are glossary is
    two lines per entry and ingestion misaligned them (half of it is the book's index), so a
    multi-line entry yields nothing. A variant spelling in brackets is dropped: "tapas (tapasya)"
    gives "tapas".
    """
    if "\n" in entry or ":" not in entry:
        return None
    head = PARENTHETICAL.sub("", entry.split(":", 1)[0]).strip()
    if len(head) < MIN_TERM_LENGTH or not TERM_PATTERN.match(head):
        return None
    return head.lower()


def _count_uses(terms: set[str], texts: Iterable[str]) -> Counter[str]:
    """
    Count how many times each term appears in the texts, as whole words.

    Every run of words as long as a term is looked up in the set of terms, one text at a time so
    that a phrase never runs across two chunks.
    """
    lengths = {len(term.split()) for term in terms}
    counts: Counter[str] = Counter()
    for text in texts:
        words = NON_WORD.sub(" ", text.lower()).split()
        for length in lengths:
            for start in range(len(words) - length + 1):
                phrase = " ".join(words[start : start + length])
                if phrase in terms:
                    counts[phrase] += 1
    return counts


def rank_terms(entries: Iterable[str], texts: Iterable[str]) -> list[str]:
    """
    Order the glossary terms by how often the texts use them, most used first.

    Terms the texts never use are dropped: they are not what a seeker will say, and this also
    removes entries that only look like terms. Ties keep alphabetical order.
    """
    terms = {term for term in map(extract_term, entries) if term}
    counts = _count_uses(terms, texts)
    return sorted(counts, key=lambda term: (-counts[term], term))


def build_prompt(
    entries: Iterable[str],
    texts: Iterable[str],
    count_tokens: Callable[[str], int],
    max_tokens: int,
) -> str:
    """
    Build the Whisper prompt: the most used glossary terms as a comma-separated list.

    Terms are added in rank order and the list is cut at the first term that would take it past
    max_tokens, so the prompt never ends on half a term.
    """
    chosen: list[str] = []
    for term in rank_terms(entries, texts):
        candidate = ", ".join([*chosen, term])
        if count_tokens(candidate) > max_tokens:
            break
        chosen.append(term)
    return ", ".join(chosen)
