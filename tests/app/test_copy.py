"""Every word a visitor can read follows the copy rules."""

import importlib
import pkgutil

import pytest

from crashmodel.app import presenters
from crashmodel.app.journey import JOURNEY
from crashmodel.app.presenters import data_sources, home
from crashmodel.app.presenters.copy import page_title
from crashmodel.data.diagnostics import HOSTED_SOURCES, Failure, SourceStatus
from tests.app.copy_rules import copy_problems


def presenter_constants() -> list[str]:
    """Every module-level text constant in the presenters, so new copy cannot dodge the rules."""
    texts: list[str] = []
    for module_info in pkgutil.iter_modules(presenters.__path__):
        module = importlib.import_module(f"{presenters.__name__}.{module_info.name}")
        texts += [
            value
            for name, value in vars(module).items()
            if name.isupper() and isinstance(value, str)
        ]
    return texts


def generated_copy() -> list[str]:
    view = home.home_view()
    cards = [text for card in view.steps for text in (card.label, card.title, card.summary)]
    journey = [text for spec in JOURNEY for text in (spec.title, spec.summary)]
    purposes = [source.purpose for source in HOSTED_SOURCES]
    headings = [view.eyebrow, view.headline, view.promise, view.status_note]
    results = [
        SourceStatus(source=HOSTED_SOURCES[0], failure=failure, status_code=503)
        for failure in (None, *Failure)
    ]
    statuses = [data_sources.describe_status(result) for result in results]
    summaries = [data_sources.summary(results[:count]) for count in range(len(results) + 1)]
    columns = list(data_sources.status_row(results[0]).as_table_row())
    return [
        *headings,
        *cards,
        *journey,
        *purposes,
        *statuses,
        *summaries,
        *columns,
        page_title("Home"),
    ]


@pytest.mark.parametrize("text", [*presenter_constants(), *generated_copy()])
def test_copy_follows_the_rules(text: str) -> None:
    assert copy_problems(text) == []


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        (f"2008 {chr(0x2013)} 2009", "dash lookalike U+2013"),
        ("Analyze your split", "American spelling 'Analyze'; use analyse"),
        ("the safest split", "reads as advice: 'safest'"),
        ("We recommend this", "reads as advice: 'recommend'"),
        ("You shouldn't worry", "reads as advice: 'shouldn'"),
        ("its suitability", "reads as advice: 'suitability'"),
    ],
)
def test_copy_rules_catch_each_kind_of_problem(text: str, problem: str) -> None:
    assert copy_problems(text) == [problem]
