"""The four-step journey that every page serves.

This registry is the single source of truth for the steps. The Home cards read from it now, and the
journey pages, progress bar and Next buttons will too, so their labels cannot drift apart.
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


JOURNEY: tuple[StepSpec, ...] = (
    StepSpec(
        title="Design",
        icon=":material/pie_chart:",
        summary="Split your money between shares, bonds and cash, or start from an example.",
    ),
    StepSpec(
        title="Stress-test",
        icon=":material/thunderstorm:",
        summary="See how each split would have coped in real crashes, side by side.",
    ),
    StepSpec(
        title="Decide",
        icon=":material/lock:",
        summary="Pick the split you are happy with and lock it in with a start date and an amount.",
    ),
    StepSpec(
        title="Track",
        icon=":material/monitoring:",
        summary="Follow how it is doing against inflation, cash and the splits you did not choose.",
    ),
)
"""The steps, in the order a visitor takes them."""
