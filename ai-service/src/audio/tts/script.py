import re

from pydantic import BaseModel, Field

# Markdown marks the model may have left in an answer; none of them is meant to be spoken.
_MARKDOWN_MARKS = re.compile(r"[*_>#`]")
_INLINE_TAG = re.compile(r"<([^<>]+)>")
# The voice director may write <short pause>, <long pause> and <breath> (see its prompt). What
# Gemini is sent as tags. A tag outside its supported list is not just ignored: it can make
# the tags after it be spoken aloud. `<long pause>` is on that list, but Flash read it aloud as
# "Long pause." in 3 of 3 takes of one teaching script (and in 1 of 10 takes in a wider test),
# while Flash-Lite does not seem to register it as a pause at all. It is therefore sent as
# ellipses, which are only punctuation and cannot be spoken as words. Two of them: the gap between
# the words measured about 2.0 s with two and 1.75 s with one (a short pause: about 1.15 s).
GEMINI_TAGS = ("short pause", "breath")
LONG_PAUSE = "long pause"
LONG_PAUSE_AS_SENT = "... ..."
# A long pause set as its own paragraph reached Gemini as "\n\n... ...\n\n" and gave 3 to 10 s of
# silence (six cases), against 1.2 to 1.7 s for the same ellipsis after a sentence, so it is
# joined to the sentence before it.
_BEFORE_LONG_PAUSE = re.compile(r"\s+(?=<\s*long pause\s*>)", re.IGNORECASE)
_WORD = re.compile(r"[\w'’-]+")


class VoiceScript(BaseModel):
    """
    What the speech model is given: the answer's words, with the pauses placed in the text.
    The voice director fills the field description in for Claude as its tool schema, so it
    is written for it.
    """

    text: str = Field(
        description=(
            "The answer's own words, unchanged and in the same order, as plain text, with "
            "inline tags where the delivery needs a pause or a breath."
        )
    )


class AudioChunk(BaseModel):
    """One piece of a streamed spoken answer: base64 audio data, in the configured format."""

    data: str


def plain_script(answer: str) -> VoiceScript:
    """The answer spoken as it stands: markdown marks removed, no pauses."""
    return VoiceScript(text=_MARKDOWN_MARKS.sub("", answer).strip())


def sanitize_tags(text: str) -> str:
    """
    The director's text as Gemini should receive it: the tags Gemini plays are kept in their
    exact spelling, a `<long pause>` becomes an ellipsis joined to the sentence before it, and
    every other <...> tag is removed.
    """
    def fix(match: re.Match[str]) -> str:
        name = match.group(1).strip().lower()
        if name in GEMINI_TAGS:
            return f"<{name}>"
        return LONG_PAUSE_AS_SENT if name == LONG_PAUSE else ""

    joined = _BEFORE_LONG_PAUSE.sub(" ", text)
    return re.sub(r" {2,}", " ", _INLINE_TAG.sub(fix, joined)).strip()


def spoken_words(text: str) -> list[str]:
    """The words a listener would hear, lowercased, without tags, marks or punctuation."""
    without_marks = _MARKDOWN_MARKS.sub("", _INLINE_TAG.sub(" ", text))
    return [word.lower() for word in _WORD.findall(without_marks)]
