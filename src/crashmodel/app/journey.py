"""The four-step journey that every page serves.

This registry is the single source of truth for the steps. The Home cards and the journey pages
take their titles and icons from it, so their labels cannot drift apart.
"""

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class StepSpec:
    """How a step is presented.

    Attributes:
        title: Short title, used in navigation and on cards.
        icon: Streamlit Material icon shortcode.
        summary: One plain-English sentence saying what the visitor does in this step.
    """

    title: str
    icon: str
    summary: str


DESIGN = StepSpec(
    title="Design",
    icon=":material/pie_chart:",
    summary="Split your money between shares, bonds and cash, or start from an example.",
)
STRESS_TEST = StepSpec(
    title="Stress-test",
    icon=":material/thunderstorm:",
    summary="See how each split would have coped in real crashes, side by side.",
)
DECIDE = StepSpec(
    title="Decide",
    icon=":material/lock:",
    summary="Pick the split you are happy with and lock it in with a start date and an amount.",
)
TRACK = StepSpec(
    title="Track",
    icon=":material/monitoring:",
    summary="Follow how it is doing against inflation, cash and the splits you did not choose.",
)

JOURNEY: tuple[StepSpec, ...] = (DESIGN, STRESS_TEST, DECIDE, TRACK)
"""The steps, in the order a visitor takes them."""
