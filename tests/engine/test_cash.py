from datetime import date

import pytest

from crashmodel.engine.cash import monthly_cash_returns
from crashmodel.engine.months import Month


def one_month(observations: list[tuple[date, float]], month: Month) -> float:
    return monthly_cash_returns(observations, month)[month]


@pytest.mark.parametrize(
    ("month", "expected"),
    [
        (Month(2021, 4), 0.0030),  # 30 days at 3.65%
        (Month(2021, 5), 0.0031),  # 31 days
        (Month(2020, 2), 0.0029),  # 29 days in a leap year, still divided by 365
    ],
)
def test_interest_accrues_for_every_calendar_day(month: Month, expected: float) -> None:
    assert one_month([(month.first_day, 3.65)], month) == pytest.approx(expected)


def test_a_rate_change_counts_from_its_day() -> None:
    april = Month(2021, 4)
    observations = [(date(2021, 4, 1), 7.30), (date(2021, 4, 16), 3.65)]
    assert one_month(observations, april) == pytest.approx(15 * 0.0002 + 15 * 0.0001)


def test_a_rate_carries_over_days_with_no_observation() -> None:
    observations = [(date(2021, 4, 1), 3.65), (date(2021, 5, 3), 3.65)]
    assert monthly_cash_returns(observations, Month(2021, 5))[Month(2021, 5)] == pytest.approx(
        0.0031
    )


def test_the_first_month_is_the_first_with_a_rate_on_its_first_day() -> None:
    observations = [(date(1975, 1, 2), 3.65), (date(1975, 2, 28), 3.65)]
    assert monthly_cash_returns(observations, Month(1975, 2)).start == Month(1975, 2)


@pytest.mark.parametrize(
    ("observations", "message"),
    [
        ([], "no rate observations"),
        ([(date(2021, 4, 2), 1.0), (date(2021, 4, 1), 1.0)], "date order"),
        ([(date(2021, 4, 1), 1.0)], "do not cover"),
        ([(date(2021, 5, 2), 1.0)], "do not cover"),
    ],
)
def test_observations_must_be_in_order_and_reach_the_last_month(
    observations: list[tuple[date, float]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        monthly_cash_returns(observations, Month(2021, 5))
