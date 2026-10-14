"""The four-step journey that every page serves.

This registry is the single source of truth for the steps: the Home cards, the navigation and,
later, the progress bar and Next buttons all read from it, so their labels cannot drift apart.
"""

from dataclasses import dataclass
from enum import StrEnum


class Step(StrEnum):
    """A step in the journey, in order."""

    DESIGN = "design"
    STRESS_TEST = "stress-test"
    DECIDE = "decide"
    TRACK = "track"


@dataclass(frozen=True)
class StepSpec:
    """How a step is presented.

    Attributes:
        step: Which step this is.
        number: Its position in the journey, from 1.
        title: Short title, used in navigation and on cards.
        icon: Streamlit Material icon shortcode.
        summary: One plain-English sentence saying what the visitor does in this step.
    """

    step: Step
    number: int
    title: str
    icon: str
    summary: str


JOURNEY: tuple[StepSpec, ...] = (
    StepSpec(
        Step.DESIGN,
        1,
        "Design",
        ":material/pie_chart:",
        "Split your money between shares, bonds and cash, or start from an example.",
    ),
    StepSpec(
        Step.STRESS_TEST,
        2,
        "Stress-test",
        ":material/thunderstorm:",
        "See how each split would have coped in real crashes, side by side.",
    ),
    StepSpec(
        Step.DECIDE,
        3,
        "Decide",
        ":material/lock:",
        "Pick the split you are happy with and lock it in with a start date and an amount.",
    ),
    StepSpec(
        Step.TRACK,
        4,
        "Track",
        ":material/monitoring:",
        "Follow how it is doing against inflation, cash and the splits you did not choose.",
    ),
)
