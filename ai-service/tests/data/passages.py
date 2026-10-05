"""
Synthetic retrieved passages in the shapes the real chunks have: talk headers, speaker labels,
names in narration, page breaks with running heads, footnote marks, citations and dates. The
sentences are invented for the tests; no source text is used.
"""
from src.rag.chunk import RetrievedChunk

DIALOGUE = RetrievedChunk(
    text=(
        "Talk 9001.\n"
        "\n"
        "A visitor from the coast asked about restlessness in the evenings. Sri Bhagavan \n"
        "listened for a while and said:\n"
        "M.: Watch the restlessness without taking its side.\n"
        "D.: It returns as soon as I stop watching.\n"
        "M.: Then notice who stops watching. Sri Bhagavan\u2019s answer was short, and \n"
        "\n"
        "412\n"
        "Talks with Sri Ramana Maharshi\n"
        "the visitor sat quietly.2\n"
        "Maharshi later added that nothing more was needed.\n"
        "3rd May, 1936"
    ),
    reference="Talk 9001",
    chunk_type="qa_pair",
    summary="summary-marker-dialogue",
    score=4.2,
)

DIALOGUE_SCRUBBED = (
    "A visitor from the coast asked about restlessness in the evenings. The teacher\n"
    "listened for a while and said:\n"
    "Answer: Watch the restlessness without taking its side.\n"
    "Question: It returns as soon as I stop watching.\n"
    "Answer: Then notice who stops watching. The teacher\u2019s answer was short, and\n"
    "the visitor sat quietly.\n"
    "The teacher later added that nothing more was needed."
)

QUESTIONS = RetrievedChunk(
    text=(
        "Q: Is it enough to sit quietly every morning?4\n"
        "A: Sitting is a start. What matters is where attention rests when the sitting ends.7\n"
        "QUIET AND ACTIVITY 88\n"
        "Q: And during work?\n"
        "A: The same attention can stay with you at work (Bh. Gita, II, 48)."
    ),
    reference="Be As You Are, Ch. 9: Quiet and activity",
    chunk_type="qa_pair",
    summary="summary-marker-questions",
    score=2.1,
)

QUESTIONS_SCRUBBED = (
    "Question: Is it enough to sit quietly every morning?\n"
    "Answer: Sitting is a start. What matters is where attention rests when the sitting ends.\n"
    "Question: And during work?\n"
    "Answer: The same attention can stay with you at work."
)

COMMENTARY = RetrievedChunk(
    text=(
        "Sri Ramana rarely gave long instructions. Newcomers were told by Sri Ramana to keep\n"
        "their attention on the sense of being themselves, and Sri Ramana\u2019s replies to\n"
        "57\n"
        "\n"
        "58\n"
        "QUIET AND ACTIVITY\n"
        "experienced visitors were often a single question. David Godman notes that the\n"
        "replies grew shorter over the years at Sri Ramanasramam."
    ),
    reference="Be As You Are, Ch. 9: Quiet and activity",
    chunk_type="passage",
    summary="summary-marker-commentary",
    score=1.3,
)

COMMENTARY_SCRUBBED = (
    "The teacher rarely gave long instructions. Newcomers were told by the teacher to keep\n"
    "their attention on the sense of being themselves, and the teacher\u2019s replies to\n"
    "experienced visitors were often a single question. The editor notes that the\n"
    "replies grew shorter over the years at the ashram."
)

TERM = RetrievedChunk(
    text="sthiti: a settled, resting state",
    reference="Glossary",
    chunk_type="glossary_entry",
    summary="summary-marker-term",
    score=0.9,
)

# The second book's glossary entries are index lines with page numbers, not definitions.
INDEX_LINES = RetrievedChunk(
    text="restlessness, 45, 88\nrest, 12, 97",
    reference="Be As You Are, Glossary",
    chunk_type="glossary_entry",
    summary="summary-marker-index",
    score=3.0,
)

UNRELATED = RetrievedChunk(
    text="Q: How should the lamp be cleaned?\nA: With a dry cloth, every week.",
    reference="Talk 9002",
    chunk_type="qa_pair",
    summary="summary-marker-unrelated",
    score=-9.5,
)

ALL_CHUNKS = [DIALOGUE, QUESTIONS, COMMENTARY, TERM, INDEX_LINES, UNRELATED]

# Background for the scenarios of round R2, one theme each, in the same shapes.

SLEEP = RetrievedChunk(
    text=(
        "Talk 9003.\n"
        "\n"
        "D.: Where does the one who wakes go in deep sleep?\n"
        "M.: Nothing is missing in sleep, yet no one is there to say so. On waking the\n"
        "sense of being someone returns, and the world with it.4"
    ),
    reference="Talk 9003",
    chunk_type="qa_pair",
    summary="summary-marker-sleep",
    score=3.6,
)

LOOKING = RetrievedChunk(
    text=(
        "Q: When I look for the one who is restless, I find only more thoughts.\n"
        "A: Then notice that the thoughts are themselves seen. Rest there for a while, without\n"
        "hunting for anything further.2"
    ),
    reference="Be As You Are, Ch. 9: Quiet and activity",
    chunk_type="qa_pair",
    summary="summary-marker-looking",
    score=2.8,
)

INQUIRY_TERM = RetrievedChunk(
    text="vichara: inquiry; turning attention to the source of the sense of I",
    reference="Glossary",
    chunk_type="glossary_entry",
    summary="summary-marker-inquiry-term",
    score=6.5,
)

BUSY_MIND = RetrievedChunk(
    text=(
        "Sri Ramana held that the mind stays busy as long as it is fed with attention. Watched\n"
        "without interest, it slows of its own accord, and the one watching is not disturbed."
    ),
    reference="Be As You Are, Ch. 9: Quiet and activity",
    chunk_type="passage",
    summary="summary-marker-busy-mind",
    score=1.9,
)

FAR_OFF = RetrievedChunk(
    text="Q: How should the lamp be cleaned?\nA: With a dry cloth, every week.",
    reference="Talk 9004",
    chunk_type="qa_pair",
    summary="summary-marker-far-off",
    score=-11.6,
)
