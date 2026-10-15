"""Charts, built with altair from presenter views.

There is no Streamlit here, so every chart can be tested on its own. Each split keeps one colour
and one dash pattern, chosen from colour-blind-safe sets, so a split is recognisable without colour
and keeps its look when other splits come and go.
"""

import altair as alt

from crashmodel.app.presenters.design import CompositionView
from crashmodel.app.presenters.stress_test import ValueChartView
from crashmodel.engine.portfolio import STARTING_VALUE

SPLIT_COLOURS = ("#0072B2", "#D55E00", "#009E73", "#9085E9")
"""Blue, vermillion, bluish green and violet: distinct with colour blindness, and at least 3:1
against both light and dark backgrounds."""
SPLIT_DASHES = ((1, 0), (6, 3), (2, 2), (8, 3, 2, 3))
"""Solid, dashed, dotted and dash-dot, so the lines differ without colour too."""
BLOCK_COLOURS = SPLIT_COLOURS
"""The same colour-blind-safe set, in block order. Blocks are coloured only on the Design page and
splits only on the Stress-test page, so a colour never means two things on one page."""
BAR_HEIGHT = 36
"""Pixels per split in the composition chart, so each bar's label has room."""
MONTH_AXIS_FORMAT = "%b %Y"
MONTH_TOOLTIP_FORMAT = "%B %Y"
POUNDS_FORMAT = ",.0f"
LEGEND_COLUMNS = 2
"""Four splits in one row overflow a phone screen; two rows of two fit at any width."""


def value_chart(view: ValueChartView) -> alt.LayerChart:
    """Draw what £100 became in each split, with a faint line at the starting £100.

    Months are read and shown in UTC, so a month never appears as the one before for a visitor
    west of London.
    """
    names = list(view.splits)
    data = alt.InlineData(
        values=[{"split": p.split, "month": p.month, "value": p.value} for p in view.points]
    )
    lines: alt.Chart = (
        alt.Chart(data)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X(
                "utcyearmonth(month):T",
                title=view.x_title,
                axis=alt.Axis(format=MONTH_AXIS_FORMAT),
                scale=alt.Scale(type="utc"),
            ),
            y=alt.Y("value:Q", title=view.y_title, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "split:N",
                title=None,
                sort=names,
                scale=alt.Scale(domain=names, range=[SPLIT_COLOURS[slot] for slot in view.slots]),
                legend=alt.Legend(orient="bottom", columns=LEGEND_COLUMNS),
            ),
            strokeDash=alt.StrokeDash(
                "split:N",
                sort=names,
                legend=None,
                scale=alt.Scale(
                    domain=names, range=[list(SPLIT_DASHES[slot]) for slot in view.slots]
                ),
            ),
            tooltip=[
                alt.Tooltip("split:N", title=view.split_title),
                alt.Tooltip(
                    "utcyearmonth(month):T", title=view.month_title, format=MONTH_TOOLTIP_FORMAT
                ),
                alt.Tooltip("value:Q", title=view.value_title, format=POUNDS_FORMAT),
            ],
        )
    )
    start: alt.Chart = (
        alt.Chart(alt.InlineData(values=[{"value": STARTING_VALUE}]))
        .mark_rule(strokeDash=[2, 2], opacity=0.6)
        .encode(y="value:Q")
    )
    return alt.LayerChart(layer=[start, lines])


def composition_chart(view: CompositionView) -> alt.Chart:
    """Draw one bar per split, divided into its building blocks in their usual order."""
    data = alt.InlineData(
        values=[
            {"split": p.split, "block": p.block, "percent": p.percent, "order": p.order}
            for p in view.points
        ]
    )
    blocks = list(view.blocks)
    chart: alt.Chart = (
        alt.Chart(data, height=BAR_HEIGHT * max(len(view.splits), 1))
        .mark_bar()
        .encode(
            y=alt.Y("split:N", sort=list(view.splits), title=None),
            x=alt.X("percent:Q", stack="zero", title=view.x_title),
            color=alt.Color(
                "block:N",
                title=None,
                sort=blocks,
                scale=alt.Scale(domain=blocks, range=list(BLOCK_COLOURS)),
                legend=alt.Legend(orient="bottom", columns=LEGEND_COLUMNS),
            ),
            order=alt.Order("order:Q"),
            tooltip=[
                alt.Tooltip("split:N", title=view.split_title),
                alt.Tooltip("block:N", title=view.block_title),
                alt.Tooltip("percent:Q", title=view.percent_title),
            ],
        )
    )
    return chart
