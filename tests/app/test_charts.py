from typing import Any

import pytest

from crashmodel.app.charts import (
    BLOCK_COLOURS,
    LEGEND_COLUMNS,
    SPLIT_COLOURS,
    SPLIT_DASHES,
    composition_chart,
    value_chart,
)
from crashmodel.app.presenters.design import CompositionPoint, CompositionView
from crashmodel.app.presenters.stress_test import ChartPoint, ValueChartView

VIEW = ValueChartView(
    points=(
        ChartPoint(split="Cautious", month="2007-06-01", value=100.0),
        ChartPoint(split="Adventurous", month="2007-06-01", value=100.0),
    ),
    splits=("Cautious", "Adventurous"),
    slots=(0, 2),
)


def lines(spec: dict[str, Any]) -> dict[str, Any]:
    layer: dict[str, Any] = spec["layer"][1]
    return layer


def test_each_split_keeps_the_colour_and_dash_of_its_slot() -> None:
    encoding = lines(value_chart(VIEW).to_dict())["encoding"]
    assert encoding["color"]["scale"] == {
        "domain": ["Cautious", "Adventurous"],
        "range": [SPLIT_COLOURS[0], SPLIT_COLOURS[2]],
    }
    assert encoding["strokeDash"]["scale"]["range"] == [
        list(SPLIT_DASHES[0]),
        list(SPLIT_DASHES[2]),
    ]


def test_months_are_read_and_shown_in_utc() -> None:
    x = lines(value_chart(VIEW).to_dict())["encoding"]["x"]
    assert x["timeUnit"] == "utcyearmonth"
    assert x["scale"]["type"] == "utc"


def test_a_faint_line_marks_the_starting_100() -> None:
    spec = value_chart(VIEW).to_dict()
    start = spec["layer"][0]
    assert start["mark"]["type"] == "rule"
    assert spec["datasets"][start["data"]["name"]] == [{"value": 100.0}]


def test_the_legend_wraps_into_rows_that_fit_a_phone() -> None:
    legend = lines(value_chart(VIEW).to_dict())["encoding"]["color"]["legend"]
    assert legend == {"orient": "bottom", "columns": LEGEND_COLUMNS}


def test_the_composition_chart_stacks_each_splits_blocks_in_order() -> None:
    view = CompositionView(
        points=(CompositionPoint(split="Mine", block="Cash", percent=100, order=3),),
        splits=("Mine",),
    )
    encoding = composition_chart(view).to_dict()["encoding"]
    assert encoding["x"]["stack"] == "zero"
    assert encoding["order"]["field"] == "order"
    assert encoding["color"]["scale"]["range"] == list(BLOCK_COLOURS)
    assert encoding["x"]["scale"]["domain"] == [0, 100]


LIGHT_BACKGROUND, DARK_BACKGROUND = "#FFFFFF", "#0E1117"
"""Streamlit's light and dark page backgrounds."""
GRAPHICS_CONTRAST = 3.0
"""The contrast WCAG asks of shapes that carry meaning, such as lines and bars."""


def luminance(colour: str) -> float:
    """The relative luminance of a #RRGGBB colour, as WCAG defines it."""
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("colour", [*SPLIT_COLOURS, *BLOCK_COLOURS])
def test_every_chart_colour_stands_out_on_light_and_dark_pages(colour: str) -> None:
    assert contrast(colour, LIGHT_BACKGROUND) >= GRAPHICS_CONTRAST
    assert contrast(colour, DARK_BACKGROUND) >= GRAPHICS_CONTRAST


def test_blocks_and_splits_never_share_a_colour() -> None:
    assert not set(BLOCK_COLOURS) & set(SPLIT_COLOURS)
