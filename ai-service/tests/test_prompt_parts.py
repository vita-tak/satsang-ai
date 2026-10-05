from pathlib import Path

import pytest

from src.agent.checks import EM_DASH, has_emoji, names_listed_name
from src.config import PROMPT_PARTS_DIR
from tests.private_names import PRIVATE_NAMES

# The owner's working copy of the prompt. It lives in the gitignored docu/ folder, so the
# comparison runs only where that file exists.
GUIDE_PROMPT_DOC = Path(__file__).resolve().parent.parent / "docu" / "satsang_guide_prompt.md"

PART_HEADINGS = {
    "1_rules.md": "## Part 1. Rules that always apply",
    "2a_pointing.md": "## Part 2a. The pointing register",
    "2b_explanatory.md": "## Part 2b. The explanatory register",
    "4_patterns.md": "## Part 4. Pattern catalog",
    "5a_social.md": "### Part 5a. Social register",
    "5b_crisis.md": "### Part 5b. Crisis instructions",
}


def doc_section(lines: list[str], heading: str) -> str:
    """
    The text of one part of the guide prompt document: from its heading to the next rule line
    ("---") or the next heading of the same or a higher level.
    """
    start = lines.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    end = start + 1
    while end < len(lines) and not ends_section(lines[end], level):
        end += 1
    return "\n".join(lines[start:end]).strip() + "\n"


def ends_section(line: str, level: int) -> bool:
    depth = len(line) - len(line.lstrip("#"))
    return line == "---" or (0 < depth <= level and line[depth:depth + 1] == " ")


def part_text(name: str) -> str:
    return (PROMPT_PARTS_DIR / name).read_text()


@pytest.mark.skipif(not GUIDE_PROMPT_DOC.exists(), reason="the guide prompt doc is not present")
@pytest.mark.parametrize(("name", "heading"), PART_HEADINGS.items())
def test_part_file_matches_the_guide_prompt_doc(name: str, heading: str) -> None:
    lines = GUIDE_PROMPT_DOC.read_text().splitlines()
    assert part_text(name) == doc_section(lines, heading)


@pytest.mark.parametrize("name", PART_HEADINGS)
def test_part_has_no_em_dash_or_emoji(name: str) -> None:
    # The project's rule for prompt text; replies may contain em dashes
    assert EM_DASH not in part_text(name)
    assert not has_emoji(part_text(name))


@pytest.mark.parametrize("name", PART_HEADINGS)
def test_part_names_no_teacher_text_or_tradition(name: str) -> None:
    assert not names_listed_name(part_text(name), "", PRIVATE_NAMES)


def test_part_3_is_not_shipped() -> None:
    assert sorted(path.name for path in PROMPT_PARTS_DIR.iterdir()) == sorted(PART_HEADINGS)
