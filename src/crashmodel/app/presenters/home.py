"""What the Home page says."""

from dataclasses import dataclass

from crashmodel.app.journey import JOURNEY
from crashmodel.app.presenters.copy import APP_NAME


@dataclass(frozen=True, kw_only=True)
class StepCard:
    """One journey step as shown on the Home page."""

    label: str
    title: str
    icon: str
    summary: str


@dataclass(frozen=True, kw_only=True)
class HomeView:
    """Everything the Home page displays."""

    eyebrow: str
    headline: str
    promise: str
    first_step: str
    second_step: str
    status_note: str
    steps: tuple[StepCard, ...]


def home_view() -> HomeView:
    """Return the Home page content: the question, the promise, the first step and the journey."""
    return HomeView(
        eyebrow=f"{APP_NAME} for UK investors",
        headline="How would your investments have coped with a crash?",
        promise=(
            "Try out different ways to split your money, see how each would have done in real "
            "crashes such as 2008 and 2020, then track the one you choose."
        ),
        first_step="See how the examples coped",
        second_step="Design your own",
        status_note=(
            "Early build: you can design splits and stress-test them now. Deciding and tracking "
            "come next."
        ),
        steps=tuple(
            StepCard(label=f"Step {number}", title=spec.title, icon=spec.icon, summary=spec.summary)
            for number, spec in enumerate(JOURNEY, start=1)
        ),
    )
