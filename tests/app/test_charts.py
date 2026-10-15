from typing import Any

from crashmodel.app.charts import SPLIT_COLOURS, SPLIT_DASHES, value_chart
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
