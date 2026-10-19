"""Where a page sits on the four-step journey."""

from dataclasses import dataclass

from crashmodel.app.journey import JOURNEY, StepSpec


@dataclass(frozen=True, kw_only=True)
class Progress:
    """How far along the journey a step is, as a fraction and in words."""

    fraction: float
    text: str


def progress(step: StepSpec) -> Progress:
    """Say which step of the journey a page is, such as "Step 2: Stress-test".

    The bar measures the whole journey, so it shows how much is still to come; the words leave out
    "of 4", which would offer steps that are still being built.
    """
    number = JOURNEY.index(step) + 1
    return Progress(fraction=number / len(JOURNEY), text=f"Step {number}: {step.title}")
