import pytest

from crashmodel.app.journey import JOURNEY, StepSpec
from crashmodel.app.presenters.progress import progress


@pytest.mark.parametrize(
    ("step", "fraction", "text"),
    [
        (JOURNEY[0], 0.25, "Step 1 of 4: Design"),
        (JOURNEY[1], 0.5, "Step 2 of 4: Stress-test"),
        (JOURNEY[2], 0.75, "Step 3 of 4: Decide"),
        (JOURNEY[3], 1.0, "Step 4 of 4: Track"),
    ],
    ids=lambda value: value.title if isinstance(value, StepSpec) else "",
)
def test_each_journey_page_says_which_step_it_is(
    step: StepSpec, fraction: float, text: str
) -> None:
    shown = progress(step)
    assert (shown.fraction, shown.text) == (fraction, text)
