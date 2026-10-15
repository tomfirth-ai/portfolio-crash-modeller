"""Every file stored in the reference folder is a known open series, with its source recorded.

This guards the privacy scan's rule that scans these files' words but not their numbers: nothing
but the registered series and their source notes may live there.
"""

from pathlib import Path

import pytest

from crashmodel.data.reference_data import REFERENCE_SERIES, ReferenceSeries, load

FOLDER = Path(__file__).resolve().parents[2] / "src/crashmodel/data/reference"


def test_the_folder_holds_only_the_registered_series_and_their_sources() -> None:
    expected = {series.path for series in REFERENCE_SERIES}
    expected |= {f"{series.folder}/SOURCE.md" for series in REFERENCE_SERIES}
    stored = {path.relative_to(FOLDER).as_posix() for path in FOLDER.rglob("*") if path.is_file()}
    assert stored == expected


@pytest.mark.parametrize("series", REFERENCE_SERIES, ids=lambda series: series.name)
def test_each_series_loads_with_plausible_values_and_no_gaps(series: ReferenceSeries) -> None:
    assert len(load(series)) > 0


@pytest.mark.parametrize("series", REFERENCE_SERIES, ids=lambda series: series.name)
def test_each_source_note_records_the_licence_and_attribution(series: ReferenceSeries) -> None:
    note = (FOLDER / series.folder / "SOURCE.md").read_text(encoding="utf-8")
    credit = series.credit
    for required in (credit.publisher, credit.licence, credit.licence_url, credit.attribution):
        assert required in note
    assert "**Retrieved:**" in note
    assert "SHA-256 `" in note
