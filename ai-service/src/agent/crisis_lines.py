"""
The verified crisis lines and emergency numbers that the owner maintains in
guide/crisis_lines.json.

A crisis reply may name only numbers from this list; the guide never makes one up. The file ships
empty, and the crisis instructions then have the guide say that it does not have the right
number and point to local emergency services or someone the person trusts.
"""
from pathlib import Path

from pydantic import BaseModel, ConfigDict, TypeAdapter


class CrisisLine(BaseModel):
    """One verified line or number, for the languages its callers are served in."""

    # A misspelt key fails at startup instead of quietly dropping a number
    model_config = ConfigDict(extra="forbid")

    country: str
    languages: list[str]
    name: str
    number: str
    note: str | None = None


def load_crisis_lines(path: Path) -> list[CrisisLine]:
    """The list, validated once at startup."""
    return TypeAdapter(list[CrisisLine]).validate_json(path.read_text(encoding="utf-8"))


def lines_for_language(lines: list[CrisisLine], language: str | None) -> list[CrisisLine]:
    """The entries for the language of the person's message, in the owner's order."""
    return [line for line in lines if language in line.languages]
