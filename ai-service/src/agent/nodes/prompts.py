import json
from typing import get_args

from src.agent.crisis_lines import CrisisLine
from src.agent.state import Direction, Intent, Situation
from src.config import DECLINE_PATH, FALLBACK_LANGUAGE, PROMPT_PARTS_DIR, TREATMENT_FALLBACK_PATH

# The guide's words are the owner's prompt parts in guide/parts/, copied verbatim from the guide
# prompt document. This module assembles them per situation, as the document's assembly table
# says, and holds the few factual lines a call adds: its dynamic inputs.

PART_FILES = {
    "1": "1_rules.md",
    "2a": "2a_pointing.md",
    "2b": "2b_explanatory.md",
    "4": "4_patterns.md",
    "5a": "5a_social.md",
    "5b": "5b_crisis.md",
}

ASSEMBLY: dict[Situation, tuple[str, ...]] = {
    "pointing": ("1", "2a", "4"),
    "explanatory": ("1", "2b"),
    "social": ("1", "5a"),
    "crisis": ("5b",),
}

PARTS = {
    part: (PROMPT_PARTS_DIR / name).read_text(encoding="utf-8").strip()
    for part, name in PART_FILES.items()
}

# The fixed reply to an off-topic message, per language. No model is called for it.
DECLINES: dict[str, str] = json.loads(DECLINE_PATH.read_text(encoding="utf-8"))

# The fixed reply to a treatment or medication message whose every written reply broke the
# treatment rule, per language: the owner's text, sent in place of the model's. Like the decline.
TREATMENT_FALLBACKS: dict[str, str] = json.loads(
    TREATMENT_FALLBACK_PATH.read_text(encoding="utf-8")
)

DIRECTIONS: tuple[Direction, ...] = get_args(Direction)
NO_DIRECTION = "none"

CRISIS_FLAG_LINE = "A crisis was flagged earlier in this conversation."

# Part 1 allows one question per reply. Haiku asked two in a few pointing replies of round R2, so
# the rule is repeated where it reads last, as the owner decided.
ONE_QUESTION_LINE = "Ask at most one question."

# The pointing reply comes through this tool so the direction of its turn is reported exactly,
# with nothing to parse.
REPLY_TOOL = {
    "name": "reply",
    "description": "Give your reply to the person and name the direction of its turn.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The reply, exactly as the person will read it.",
            },
            "direction": {
                "type": "string",
                "enum": [*DIRECTIONS, NO_DIRECTION],
                "description": (
                    "The direction of the turn in this reply, as named in part 2a, or none "
                    "when there is no turn."
                ),
            },
        },
        "required": ["text", "direction"],
        "additionalProperties": False,
    },
}


def system_prompt(situation: Situation) -> str:
    """The parts the assembly table lists for the situation, joined, and nothing else."""
    return "\n\n".join(PARTS[part] for part in ASSEMBLY[situation])


def decline_message(language: str | None) -> str:
    """The decline in the language of the person's message, or in English."""
    return DECLINES.get(language or FALLBACK_LANGUAGE, DECLINES[FALLBACK_LANGUAGE])


def treatment_fallback_message(language: str | None) -> str:
    """The fixed treatment reply in the language of the person's message, or in English."""
    fallbacks = TREATMENT_FALLBACKS
    return fallbacks.get(language or FALLBACK_LANGUAGE, fallbacks[FALLBACK_LANGUAGE])


def user_turn(message: str, facts: list[str], background: list[str] | None = None) -> str:
    """
    The user turn of a generation call: the retrieved context when the situation has one, the
    person's message, then the call's dynamic facts. The facts come last because Haiku follows
    what it reads last more closely than system text that a long message has pushed far back.
    """
    blocks = [] if background is None else [_context_block(background)]
    blocks.append(f"The person's message:\n{message}")
    if facts:
        blocks.append("\n".join(facts))
    return "\n\n---\n\n".join(blocks)


def language_line(language: str) -> str:
    return f"Language of the person's message: {language}."


def directions_line(recent: list[Direction]) -> str:
    used = ", ".join(recent) if recent else "none yet"
    return f"Directions used in the last two replies: {used}."


def avoid_words_line(words: list[str]) -> str:
    """
    The line that closes the request for a rewritten reply that used banned words about a
    treatment: which words, and what to do instead.
    """
    quoted = [f'"{word}"' for word in words]
    if len(quoted) == 1:
        used, them = f"the word {quoted[0]}", "it"
    else:
        used, them = f"the words {', '.join(quoted[:-1])} and {quoted[-1]}", "them"
    return (
        f"Your previous reply used {used}, which this reply must not use. Write the reply again "
        f"without {them}, and without connecting the treatment to meditation."
    )


def forbidden_directions_line(recent: list[Direction]) -> str:
    return f"Forbidden directions for this reply: {', '.join(recent)}."


def crisis_lines_block(lines: list[CrisisLine]) -> str:
    if not lines:
        return (
            "Verified crisis lines for this language: none. Name no phone number. Follow step 3 "
            "for when no number is provided."
        )
    entries = "\n".join(_crisis_line(line) for line in lines)
    return f"Verified crisis lines for this language:\n{entries}"


def _crisis_line(line: CrisisLine) -> str:
    entry = f"{line.country}: {line.name}, {line.number}"
    return f"{entry} ({line.note})" if line.note else entry


def _context_block(passages: list[str]) -> str:
    if not passages:
        return "Retrieved context: none that speaks to this message with confidence."
    return "Retrieved context:\n\n" + "\n\n---\n\n".join(passages)


# The guide's voice. The speaker sends VOICE_STYLE with every spoken answer, so the guide sounds
# like one person whatever the seeker brings; the voice director only places the pauses.

VOICE_STYLE = (
    "Speak plainly in a calm, grounded, unhurried voice, at a natural, even pace, as one person "
    "talking with another. Keep the same pace, tone and energy throughout, whatever the words "
    "are about: an explanation, an instruction, a question and a word of comfort all sound "
    "alike, in the same everyday voice."
)

VOICE_DIRECTOR = """\
You are the voice director for an AI guide to self-inquiry in the tradition of Ramana \
Maharshi. You receive the guide's finished answer, and prepare it to be spoken aloud by a \
speech model that reads exactly what you write.

Keep the answer's own words, unchanged and in the same order: you add nothing, remove nothing \
and reword nothing, since the seeker may also be reading the answer on the page. Write plain \
text, without markdown marks. A reference after a quotation is read as it stands.

The guide speaks in one voice in every answer: calm, grounded and unhurried, at a natural \
pace. That voice is already set, whatever the answer is about, so its pace, tone and feeling \
are not yours to change. What you decide is where the silences fall.

Inside the text you may place the tags <short pause>, <long pause> and <breath>. An unhurried \
voice already leaves room between sentences, so a tag adds a real silence: a short pause is \
about a second, a long pause about two. Place one where a listener, hearing the words once, \
needs a moment for a thought to land, such as where an explanation turns, or after a sentence \
that sends them back to themselves. A long pause is rare, usually one at most: before a \
closing question set apart as its own paragraph, or after something they are asked to try \
now. A breath is rarer still, before a new thought. Pause for meaning, never for mood: extra \
silences make the guide sound slow and heavy. The same rhythm runs through every answer, and \
what the seeker is doing shifts it only a little, as the note below says."""

# What the seeker is doing shifts the pauses a little, never the voice. Off-topic replies never
# reach the director.
VOICE_NOTES: dict[Intent, str] = {
    "teaching": (
        "The seeker asked about the teachings or the nature of things. This is the usual "
        "rhythm: a short pause where the explanation turns, a long pause before a closing "
        "question."
    ),
    "practice": (
        "The seeker is being guided in the practice, or is answering the guide's question. "
        "When the answer asks them to look at something or try it now, a short pause after "
        "it gives them the moment to do so."
    ),
    "struggle": (
        "The seeker is sharing a difficulty. Keep the usual rhythm: the voice is already "
        "steady and unhurried, and that steadiness is what helps, so add no silences for the "
        "weight of what they said. A short pause after the sentence that meets them can let "
        "it land."
    ),
    "definition": (
        "The seeker asked what a term means. The meaning reads straight through, with fewer "
        "pauses than usual; a closing question, if there is one, still has its pause."
    ),
    "social": (
        "The seeker is greeting, thanking or saying goodbye. Read it through as it would be "
        "said, with no long pause."
    ),
    "crisis": (
        "The seeker may be in danger. Every word must reach them clearly: no long pause and "
        "no breath, and a short pause only where it helps them take in what to do."
    ),
}


def voice_director_prompt(intent: Intent) -> str:
    """The system prompt for the voice director: its task, then the note for the intent."""
    return f"{VOICE_DIRECTOR}\n\nThe note for this answer: {VOICE_NOTES[intent]}"
