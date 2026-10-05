import pytest

from src.agent.background import background_passages, copy_sources, scrub
from src.agent.checks import names_listed_name
from tests.data.passages import (
    ALL_CHUNKS,
    COMMENTARY,
    COMMENTARY_SCRUBBED,
    DIALOGUE,
    DIALOGUE_SCRUBBED,
    INDEX_LINES,
    QUESTIONS,
    QUESTIONS_SCRUBBED,
    TERM,
    UNRELATED,
)
from tests.private_names import PRIVATE_NAMES

THRESHOLD = 0.0


@pytest.mark.parametrize(
    ("chunk", "expected"),
    [
        (DIALOGUE, DIALOGUE_SCRUBBED),
        (QUESTIONS, QUESTIONS_SCRUBBED),
        (COMMENTARY, COMMENTARY_SCRUBBED),
    ],
)
def test_scrub_leaves_a_passage_that_reads_naturally(chunk, expected: str) -> None:
    assert scrub(chunk.text) == expected


def test_scrub_joins_a_sentence_split_by_a_page_break() -> None:
    assert "short, and\nthe visitor sat quietly." in scrub(DIALOGUE.text)


def test_scrub_keeps_a_paragraph_break_after_a_page_break() -> None:
    text = "It ended there.\n\n356\nTalks with Sri Ramana Maharshi\n\nD.: Then what?"
    assert scrub(text) == "It ended there.\n\nQuestion: Then what?"


def test_scrub_capitalises_a_name_replaced_at_the_start_of_a_sentence() -> None:
    assert scrub("He paused. Maharshi smiled.") == "He paused. The teacher smiled."


def test_scrub_leaves_no_double_spaces_or_stray_honorifics() -> None:
    for chunk in (DIALOGUE, QUESTIONS, COMMENTARY):
        scrubbed = scrub(chunk.text)
        assert "  " not in scrubbed
        assert "Sri" not in scrubbed


def test_background_keeps_relevant_passages_in_order() -> None:
    assert background_passages(ALL_CHUNKS, THRESHOLD) == [
        DIALOGUE_SCRUBBED,
        QUESTIONS_SCRUBBED,
        COMMENTARY_SCRUBBED,
        TERM.text,
    ]


def test_background_drops_index_lines_from_the_book_glossary() -> None:
    assert background_passages([INDEX_LINES], THRESHOLD) == []


def test_background_drops_chunks_below_the_threshold() -> None:
    assert background_passages([UNRELATED], THRESHOLD) == []


def test_background_is_empty_when_no_chunk_passes_the_threshold() -> None:
    assert background_passages(ALL_CHUNKS, min_score=10.0) == []


def test_copy_sources_leave_out_glossary_definitions() -> None:
    assert copy_sources(ALL_CHUNKS, THRESHOLD) == [
        DIALOGUE_SCRUBBED,
        QUESTIONS_SCRUBBED,
        COMMENTARY_SCRUBBED,
    ]


def test_background_carries_no_name_title_or_metadata() -> None:
    passages = "\n".join(background_passages(ALL_CHUNKS, THRESHOLD))
    assert not names_listed_name(passages, "", PRIVATE_NAMES)
    for chunk in ALL_CHUNKS:
        assert chunk.reference not in passages
        assert chunk.summary not in passages
