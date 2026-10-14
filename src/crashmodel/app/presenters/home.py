"""What the Home page says."""

from dataclasses import dataclass

from crashmodel.app.journey import JOURNEY
from crashmodel.app.presenters.copy import APP_NAME


@dataclass(frozen=True)
class StepCard:
    """One journey step as shown on the Home page."""

    label: str
    title: str
    icon: str
    summary: str


@dataclass(frozen=True)
class HomeView:
    """Everything the Home page displays."""

    eyebrow: str
    headline: str
    promise: str
    steps: tuple[StepCard, ...]
    status_note: str


def home_view() -> HomeView:
    """Return the Home page content: the question, the promise and the four steps."""
    return HomeView(
        eyebrow=f"{APP_NAME} for UK investors",
        headline="How would your investments have coped with a crash?",
        promise=(
            "Try out different ways to split your money, see how each would have done in real "
            "crashes such as 2008 and 2020, then track the one you choose."
        ),
        steps=tuple(
            StepCard(f"Step {spec.number}", spec.title, spec.icon, spec.summary) for spec in JOURNEY
        ),
        status_note="Early build: the four steps are being built now, in this order.",
    )
