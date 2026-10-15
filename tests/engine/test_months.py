from datetime import date

import pytest

from crashmodel.engine.months import Month, MonthlySeries, month_range

JUNE_2007 = Month(2007, 6)


def test_months_are_written_and_read_as_year_and_month() -> None:
    assert str(JUNE_2007) == "2007-06"
    assert Month.parse("2007-06") == JUNE_2007
    assert Month.of(date(2007, 6, 29)) == JUNE_2007


@pytest.mark.parametrize("text", ["2007-6", "2007-06-30", "June 2007", "2007-13"])
def test_badly_written_months_are_rejected(text: str) -> None:
    with pytest.raises(ValueError, match="month"):
        Month.parse(text)


@pytest.mark.parametrize(
    ("first", "months", "expected"),
    [
        (Month(2007, 6), 1, Month(2007, 7)),
        (Month(2007, 12), 1, Month(2008, 1)),
        (Month(2008, 1), -1, Month(2007, 12)),
        (Month(2007, 6), 60, Month(2012, 6)),
    ],
)
def test_adding_months_rolls_over_years(first: Month, months: int, expected: Month) -> None:
    assert first + months == expected


@pytest.mark.parametrize(
    ("later", "earlier", "months"),
    [
        (Month(2009, 2), Month(2007, 10), 16),
        (Month(2012, 6), Month(2007, 6), 60),
        (Month(2020, 3), Month(2019, 12), 3),
        (Month(2007, 6), Month(2007, 6), 0),
    ],
)
def test_subtracting_months_counts_the_months_between(
    later: Month, earlier: Month, months: int
) -> None:
    assert later - earlier == months


def test_the_month_before_crosses_years() -> None:
    assert Month(2008, 1).previous == Month(2007, 12)


def test_months_know_their_length_and_last_day() -> None:
    assert Month(2020, 2).days == 29
    assert Month(2021, 2).last_day == date(2021, 2, 28)


def test_month_range_includes_both_ends() -> None:
    assert list(month_range(Month(2007, 11), Month(2008, 2))) == [
        Month(2007, 11),
        Month(2007, 12),
        Month(2008, 1),
        Month(2008, 2),
    ]


SERIES = MonthlySeries(Month(2007, 11), (0.1, 0.2, 0.3, 0.4))


def test_a_series_knows_its_months_and_values() -> None:
    assert SERIES.end == Month(2008, 2)
    assert len(SERIES) == 4
    assert SERIES[Month(2008, 1)] == 0.3
    assert [str(month) for month, _ in SERIES.items()] == [
        "2007-11",
        "2007-12",
        "2008-01",
        "2008-02",
    ]


def test_a_series_refuses_months_it_does_not_have() -> None:
    with pytest.raises(KeyError, match="outside"):
        SERIES[Month(2008, 3)]


def test_a_series_can_be_cut_to_a_range_it_covers() -> None:
    assert SERIES.covers(Month(2007, 12), Month(2008, 2))
    assert not SERIES.covers(Month(2007, 10), Month(2008, 2))
    assert SERIES.between(Month(2007, 12), Month(2008, 1)) == MonthlySeries(
        Month(2007, 12), (0.2, 0.3)
    )
    with pytest.raises(KeyError, match="not inside"):
        SERIES.between(Month(2008, 1), Month(2008, 6))


def test_a_series_built_from_pairs_must_have_no_gaps() -> None:
    pairs = [(Month(2020, 1), 1.0), (Month(2020, 2), 2.0)]
    assert MonthlySeries.from_pairs(pairs) == MonthlySeries(Month(2020, 1), (1.0, 2.0))
    with pytest.raises(ValueError, match="no gaps"):
        MonthlySeries.from_pairs([(Month(2020, 1), 1.0), (Month(2020, 3), 2.0)])


def test_a_series_cannot_be_empty() -> None:
    with pytest.raises(ValueError, match="at least one value"):
        MonthlySeries(JUNE_2007, ())
    with pytest.raises(ValueError, match="at least one value"):
        MonthlySeries.from_pairs([])
