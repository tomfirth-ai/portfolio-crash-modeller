import pytest

from crashmodel.engine.episodes import (
    COVID,
    EPISODES,
    GLOBAL_FINANCIAL_CRISIS,
    Episode,
    missing_holdings,
    run_episode,
)
from crashmodel.engine.months import Month, MonthlySeries


def test_each_episode_spans_five_years_of_returns() -> None:
    for episode in EPISODES:
        assert episode.end - episode.start == 60


def test_the_financial_crisis_needs_returns_from_july_2007_to_june_2012() -> None:
    weights = {"shares": 1.0}
    exact = {"shares": MonthlySeries(Month(2007, 7), (0.0,) * 60)}
    one_short = {"shares": MonthlySeries(Month(2007, 7), (0.0,) * 59)}
    assert missing_holdings(GLOBAL_FINANCIAL_CRISIS, weights, exact) == []
    assert missing_holdings(GLOBAL_FINANCIAL_CRISIS, weights, one_short) == ["shares"]
    assert run_episode(GLOBAL_FINANCIAL_CRISIS, weights, exact).result.end_value == 100


def test_the_covid_crash_phase_ends_mid_2020() -> None:
    assert (COVID.start, COVID.crash_end) == (Month(2019, 12), Month(2020, 6))


def test_an_episode_must_have_its_months_in_order() -> None:
    with pytest.raises(ValueError, match="start < crash end <= end"):
        Episode(key="bad", start=Month(2020, 6), crash_end=Month(2020, 1), end=Month(2021, 1))


EPISODE = Episode(key="test", start=Month(2020, 1), crash_end=Month(2020, 3), end=Month(2020, 4))
SHARES = MonthlySeries(Month(2020, 2), (-0.2, -0.25, 0.5))
SHORT = MonthlySeries(Month(2020, 2), (0.0, 0.0))


def test_holdings_without_returns_for_the_whole_episode_are_named() -> None:
    weights = {"shares": 0.5, "bonds": 0.3, "cash": 0.2, "gold": 0.0}
    returns = {"shares": SHARES, "bonds": SHORT}
    assert missing_holdings(EPISODE, weights, returns) == ["bonds", "cash"]


def test_a_split_is_run_through_the_episode() -> None:
    run = run_episode(EPISODE, {"shares": 1.0}, {"shares": SHARES})
    assert run.values.values == pytest.approx((100, 80, 60, 90))
    result = run.result
    assert result.fall is not None
    assert result.fall.depth == pytest.approx(0.40)
    assert result.end_value == pytest.approx(90)
