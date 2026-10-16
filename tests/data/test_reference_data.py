from pathlib import Path

import pytest

from crashmodel.data.reference_data import (
    STERLING_CASH_RETURN,
    USD_PER_GBP,
    load,
    parse_series,
    reference_folder,
    stored,
)
from crashmodel.engine.months import Month, MonthlySeries

GOOD = "month,usd_per_gbp\n2020-01,2.1000\n2020-02,2.2000\n"


def test_a_stored_series_is_read_into_months_and_values() -> None:
    assert parse_series(USD_PER_GBP, GOOD) == MonthlySeries(Month(2020, 1), (2.1, 2.2))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "must start with the header"),
        ("month,cash_return\n2020-01,0.001\n", "must start with the header"),
        ("month,usd_per_gbp\n2020-01,two\n", "expected YYYY-MM,<number>"),
        ("month,usd_per_gbp\n2020-01,2.1,extra\n", "expected YYYY-MM,<number>"),
        ("month,usd_per_gbp\n2020-01,50.0\n", "value outside"),
        ("month,usd_per_gbp\n2020-01,2.1\n2020-03,2.2\n", "no gaps"),
    ],
)
def test_a_malformed_series_is_refused(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_series(USD_PER_GBP, text)


def test_a_series_is_loaded_from_its_folder(tmp_path: Path) -> None:
    (tmp_path / STERLING_CASH_RETURN.folder).mkdir()
    (tmp_path / STERLING_CASH_RETURN.path).write_text("month,cash_return\n2020-01,0.0010000000\n")
    assert load(STERLING_CASH_RETURN, tmp_path) == MonthlySeries(Month(2020, 1), (0.001,))


def test_each_series_names_its_file_and_header() -> None:
    assert (USD_PER_GBP.path, USD_PER_GBP.header) == (
        "fed-h10/usd_per_gbp.csv",
        "month,usd_per_gbp",
    )


def test_the_stored_series_live_in_the_packages_reference_folder() -> None:
    assert reference_folder().name == "reference"


def test_the_packaged_copy_of_a_series_is_read_once() -> None:
    assert stored(STERLING_CASH_RETURN) is stored(STERLING_CASH_RETURN)
    assert stored(STERLING_CASH_RETURN) == load(STERLING_CASH_RETURN)
