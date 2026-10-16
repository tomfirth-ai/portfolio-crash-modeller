from datetime import date

import pytest

from crashmodel.engine.cash import monthly_cash_returns
from crashmodel.engine.months import Month


def one_month(observations: list[tuple[date, float]], month: Month) -> float:
    return monthly_cash_returns(observations, month)[month]


DAY_AT_3_65 = 1.0001
"""A day's growth at 3.65% a year: 3.65 / 100 / 365 = 0.0001."""


@pytest.mark.parametrize(
    ("month", "days"),
    [
        (Month(2021, 4), 30),
        (Month(2021, 5), 31),
        (Month(2020, 2), 29),  # a leap year's February, still at 1/365 of the rate a day
    ],
)
def test_interest_compounds_on_every_calendar_day(month: Month, days: int) -> None:
    assert one_month([(month.first_day, 3.65)], month) == pytest.approx(DAY_AT_3_65**days - 1)


def test_compounding_earns_a_little_more_than_simple_interest() -> None:
    assert one_month([(date(2021, 5, 1), 3.65)], Month(2021, 5)) > 31 * 0.0001


def test_a_rate_change_counts_from_its_day() -> None:
    april = Month(2021, 4)
    observations = [(date(2021, 4, 1), 7.30), (date(2021, 4, 16), 3.65)]
    assert one_month(observations, april) == pytest.approx(1.0002**15 * DAY_AT_3_65**15 - 1)


def test_a_rate_carries_over_days_with_no_observation() -> None:
    observations = [(date(2021, 4, 1), 3.65), (date(2021, 5, 3), 3.65)]
    assert monthly_cash_returns(observations, Month(2021, 5))[Month(2021, 5)] == pytest.approx(
        DAY_AT_3_65**31 - 1
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
