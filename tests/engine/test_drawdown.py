import pytest
from hypothesis import given
from hypothesis import strategies as st

from crashmodel.engine.drawdown import crash_result
from crashmodel.engine.months import Month, MonthlySeries

START = Month(2007, 6)


def path(*values: float) -> MonthlySeries:
    return MonthlySeries(START, values)


def at(index: int) -> Month:
    return START + index


def test_a_fall_from_the_start_and_back() -> None:
    result = crash_result(path(100, 90, 72, 108), crash_end=at(3))
    fall = result.fall
    assert fall is not None
    assert (fall.peak, fall.bottom, fall.recovery) == (at(0), at(2), at(3))
    assert fall.depth == pytest.approx(0.28)
    assert (fall.months_to_bottom, fall.months_to_recover) == (2, 1)
    assert result.end_value == 108


def test_a_fall_that_has_not_recovered_by_the_end() -> None:
    result = crash_result(path(100, 125, 100, 50, 75), crash_end=at(4))
    fall = result.fall
    assert fall is not None
    assert (fall.peak, fall.bottom) == (at(1), at(3))
    assert fall.depth == pytest.approx(0.60)
    assert (fall.recovery, fall.months_to_recover) == (None, None)
    assert result.end_value == 75


def test_getting_back_exactly_to_the_high_counts_as_recovered() -> None:
    fall = crash_result(path(100, 50, 100), crash_end=at(1)).fall
    assert fall is not None
    assert fall.recovery == at(2)


def test_a_float_near_miss_counts_as_recovered() -> None:
    fall = crash_result(path(100, 60, 60 * (1 + 2 / 3)), crash_end=at(1)).fall
    assert fall is not None
    assert fall.recovery == at(2)


def test_the_high_point_is_the_latest_month_at_that_high() -> None:
    fall = crash_result(path(100, 110, 100, 110, 88, 110), crash_end=at(5)).fall
    assert fall is not None
    assert (fall.peak, fall.bottom, fall.recovery) == (at(3), at(4), at(5))
    assert fall.depth == pytest.approx(0.20)


def test_of_two_equal_falls_the_earlier_is_reported() -> None:
    fall = crash_result(path(100, 80, 100, 80, 120), crash_end=at(4)).fall
    assert fall is not None
    assert (fall.bottom, fall.recovery) == (at(1), at(2))


def test_a_split_that_never_fell_has_no_fall() -> None:
    result = crash_result(path(100, 100.3, 100.61, 100.9), crash_end=at(3))
    assert result.fall is None
    assert result.end_value == 100.9


def test_falls_after_the_crash_phase_and_after_recovery_are_left_out() -> None:
    fall = crash_result(path(100, 90, 95, 100, 70, 100), crash_end=at(2)).fall
    assert fall is not None
    assert (fall.bottom, fall.recovery, fall.deeper_later) == (at(1), at(3), None)
    assert fall.depth == pytest.approx(0.10)


def test_a_deeper_low_after_the_crash_phase_is_flagged() -> None:
    fall = crash_result(path(100, 95, 97, 80, 100), crash_end=at(1)).fall
    assert fall is not None
    assert fall.depth == pytest.approx(0.05)
    assert fall.deeper_later == pytest.approx(0.20)
    assert (fall.recovery, fall.months_to_recover) == (at(4), 3)


def test_a_bottom_in_the_last_month_of_the_crash_phase_may_not_be_the_end() -> None:
    fall = crash_result(path(100, 90, 80, 85), crash_end=at(2)).fall
    assert fall is not None
    assert fall.still_falling


@pytest.mark.parametrize("crash_end", [START, at(4)])
def test_the_crash_phase_must_end_inside_the_window(crash_end: Month) -> None:
    with pytest.raises(ValueError, match="must be after"):
        crash_result(path(100, 90, 95), crash_end=crash_end)


value_paths = st.lists(st.floats(min_value=1.0, max_value=1000.0), min_size=2, max_size=24)


@given(value_paths)
def test_a_fall_is_between_nothing_and_everything(values: list[float]) -> None:
    fall = crash_result(MonthlySeries(START, tuple(values)), crash_end=at(1)).fall
    assert fall is None or 0 < fall.depth < 1


@given(value_paths, st.floats(min_value=0.1, max_value=100.0))
def test_the_fall_does_not_depend_on_the_starting_amount(values: list[float], scale: float) -> None:
    original = crash_result(MonthlySeries(START, tuple(values)), crash_end=at(1)).fall
    scaled = crash_result(MonthlySeries(START, tuple(v * scale for v in values)), at(1)).fall
    assert (original is None) == (scaled is None)
    if original is not None and scaled is not None:
        assert scaled.depth == pytest.approx(original.depth, abs=1e-9)
        assert (scaled.bottom, scaled.recovery) == (original.bottom, original.recovery)
