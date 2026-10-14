from pathlib import Path

import pytest

from tools import check_style
from tools.check_style import DASH_LOOKALIKES


@pytest.mark.parametrize("character", sorted(DASH_LOOKALIKES))
def test_every_dash_lookalike_is_flagged(character: str) -> None:
    problems = check_style.check_text(f"one {character} two", "file.txt", prose=False)
    assert len(problems) == 1
    assert problems[0].line == 1


def test_plain_hyphens_pass() -> None:
    assert check_style.check_text("well-known, 2008 to 2009", "file.md", prose=True) == []


def test_american_spellings_in_prose_are_flagged_with_the_british_form() -> None:
    problems = check_style.check_text("Intro\nThe color of money", "README.md", prose=True)
    assert [(problem.line, "colour" in problem.message) for problem in problems] == [(2, True)]


def test_code_and_links_are_not_spell_checked() -> None:
    markdown = "Set `color` here\n```python\ncolor = 1\n```\n[guide](https://example.com/color)\n"
    assert check_style.check_text(markdown, "README.md", prose=True) == []


def test_line_numbers_survive_blanked_code_blocks() -> None:
    markdown = "```\ncode\n```\nThe gray area\n"
    problems = check_style.check_text(markdown, "README.md", prose=True)
    assert [problem.line for problem in problems] == [4]


def test_spelling_rules_apply_to_prose_only() -> None:
    assert check_style.check_text("color = 'red'", "app.py", prose=False) == []


def test_main_checks_a_commit_message(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text(f"Fix the colour {chr(0x2014)} at last\n", encoding="utf-8")
    assert check_style.main(["--message", str(message)]) == 1


def test_main_checks_named_files(tmp_path: Path) -> None:
    clean = tmp_path / "clean.md"
    clean.write_text("Behaviour is analysed.\n", encoding="utf-8")
    assert check_style.main([str(clean)]) == 0
