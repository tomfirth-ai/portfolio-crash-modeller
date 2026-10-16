"""The journey end to end, through the real app: design splits, then stress-test them.

Every return here is made up, so each figure the page shows can be worked out by hand.
"""

import json
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from crashmodel.app import loaders, state
from crashmodel.app.charts import SPLIT_COLOURS
from crashmodel.app.presenters import design, home, stress_test
from crashmodel.app.splits import CAUTIOUS, EXAMPLE_SPLITS
from crashmodel.app.state import HOLDINGS, INCLUDED, NAME, TEMPLATE, percent_key, widget_key
from crashmodel.data.models import IndexModel
from crashmodel.data.panel import Panel
from crashmodel.engine.episodes import COVID
from crashmodel.engine.months import Month, MonthlySeries, month_range
from crashmodel.engine.portfolio import Rebalancing
from tests.app.running import (
    DESIGN_PAGE,
    STRESS_TEST_PAGE,
    button,
    button_group,
    captions,
    click,
    click_through,
    run_app,
)

FIRST, LAST = Month(2007, 7), Month(2024, 12)
SHARE_MOVES = {Month(2008, 10): -0.40, Month(2009, 3): 0.50}
"""FTSE All-World loses 40% in October 2008 and gains 50% in March 2009; nothing else moves."""


def synthetic_panel(_models: object = ()) -> Panel:
    months = list(month_range(FIRST, LAST))
    still = MonthlySeries(FIRST, (0.0,) * len(months))
    shares = MonthlySeries(FIRST, tuple(SHARE_MOVES.get(month, 0.0) for month in months))
    returns = dict.fromkeys(IndexModel, still) | {IndexModel.GLOBAL_LARGE: shares}
    return Panel(returns=returns, unavailable=frozenset(), vintages={})


@pytest.fixture(autouse=True)
def synthetic_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loaders, "load_panel", synthetic_panel)


def designed_half_and_half() -> AppTest:
    """A visitor's own split, half in FTSE All-World and half in cash, sent to the Stress-test.

    The first holding chosen starts at 100% and the second at 0%, so only the first is changed.
    """
    app = click_through(run_app(), home.home_view().second_step, DESIGN_PAGE)
    click(app, design.START_OWN)
    app.text_input(key=widget_key(0, NAME)).input("Half and half").run()
    app.multiselect(key=widget_key(0, HOLDINGS)).select("ftse_all_world").run()
    assert app.number_input(key=percent_key(0, "ftse_all_world")).value == 100
    app.multiselect(key=widget_key(0, HOLDINGS)).select("bank_rate").run()
    assert app.number_input(key=percent_key(0, "bank_rate")).value == 0
    app.number_input(key=percent_key(0, "ftse_all_world")).set_value(50).run()
    app.number_input(key=percent_key(0, "bank_rate")).set_value(50).run()
    return click_through(app, design.NEXT, STRESS_TEST_PAGE)


def test_a_visitor_designs_a_split_and_sees_it_through_the_2008_crash() -> None:
    """Half in FTSE All-World, half in cash, kept at its weights, through the 2007-09 window.

    The split is worth 100 until September 2008. In October its shares lose 40%, which is 20 of
    every 100, so it falls 20% one month after that high. Put back to half and half, it holds 40 in
    shares when they gain 50% in March 2009, so it is back at 100 five months after the bottom.
    """
    app = designed_half_and_half()

    assert app.title[0].value == stress_test.TITLE
    assert app.table[0].value.to_dict("records") == [
        {
            "Split": "Half and half",
            "Worst fall in the crash": "20%",
            "Months to the bottom": "1",
            "Months to get back": "5",
            "£100 became": "£100",
        }
    ]
    paragraphs = [markdown.value for markdown in app.markdown]
    assert (
        "Half and half fell 20% at worst in the crash phase. It hit bottom 1 month after its high "
        "and took another 5 months to get back to that high. £100 at the start was worth £100 by "
        "June 2012."
    ) in paragraphs
    assert (
        "Of every £100 it had at its high, FTSE All-World (modelled) lost £20.00 on the way down "
        "to its low in the crash phase."
    ) in paragraphs


def test_a_split_left_alone_ends_where_its_drifted_weights_take_it() -> None:
    """Left alone after the fall, the split holds 30 in shares and 50 in cash.

    The 50% rise in March 2009 lifts it only to 95, so it is not back at its high by June 2012.
    """
    app = designed_half_and_half()
    button_group(app, state.MANAGEMENT).set_value(Rebalancing.NEVER.value).run()

    row = app.table[0].value.to_dict("records")[0]
    assert (row["Months to get back"], row["£100 became"]) == ("Not by June 2012", "£95")


def test_a_split_that_does_not_add_up_holds_back_the_next_step() -> None:
    app = run_app(DESIGN_PAGE)
    app.number_input(key=percent_key(1, "uk_gilt")).set_value(45).run()

    assert button(app, design.NEXT).disabled
    assert "Balanced adds up to 105%, not 100%." in captions(app)

    app.switch_page(STRESS_TEST_PAGE).run()
    assert app.warning[0].value == "Balanced is left out, because it adds up to 105%, not 100%."
    assert "Balanced" not in list(app.table[0].value["Split"])


def chart_colours(app: AppTest) -> list[str]:
    [chart] = app.get("vega_lite_chart")
    spec: dict[str, Any] = json.loads(chart.proto.spec)
    colours: list[str] = spec["layer"][1]["encoding"]["color"]["scale"]["range"]
    return colours


def test_switching_a_split_off_leaves_the_others_their_colours() -> None:
    app = run_app(DESIGN_PAGE)
    app.toggle(key=widget_key(0, INCLUDED)).set_value(False).run()
    app.switch_page(STRESS_TEST_PAGE).run()

    assert chart_colours(app) == list(SPLIT_COLOURS[1:])


def test_with_every_split_switched_off_the_stress_test_says_what_to_do() -> None:
    app = run_app(DESIGN_PAGE)
    for index in range(len(SPLIT_COLOURS)):
        app.toggle(key=widget_key(index, INCLUDED)).set_value(False).run()

    assert button(app, design.NEXT).disabled
    app.switch_page(STRESS_TEST_PAGE).run()
    assert app.info[0].value == stress_test.NO_SPLITS
    assert not app.table


def test_one_visitors_changes_never_reach_another() -> None:
    first = run_app(DESIGN_PAGE)
    first.text_input(key=widget_key(0, NAME)).input("Changed").run()
    first.number_input(key=percent_key(0, "bank_rate")).set_value(0).run()

    second = run_app(DESIGN_PAGE)
    assert second.text_input(key=widget_key(0, NAME)).value == "Cautious"
    assert second.number_input(key=percent_key(0, "bank_rate")).value == 20


def test_a_visitors_splits_survive_a_visit_to_another_page() -> None:
    app = run_app(DESIGN_PAGE)
    app.text_input(key=widget_key(0, NAME)).input("Kept").run()
    app.switch_page(STRESS_TEST_PAGE).run()
    app.switch_page(DESIGN_PAGE).run()

    assert app.text_input(key=widget_key(0, NAME)).value == "Kept"


def test_the_chosen_crash_survives_a_visit_to_another_page() -> None:
    app = run_app(STRESS_TEST_PAGE)
    button_group(app, state.CRASH).set_value(COVID.key).run()
    app.switch_page(DESIGN_PAGE).run()
    app.switch_page(STRESS_TEST_PAGE).run()

    assert button_group(app, state.CRASH).value == COVID.key


def test_the_chosen_way_of_managing_splits_survives_a_visit_to_another_page() -> None:
    app = run_app(STRESS_TEST_PAGE)
    button_group(app, state.MANAGEMENT).set_value(Rebalancing.NEVER.value).run()
    app.switch_page(DESIGN_PAGE).run()
    app.switch_page(STRESS_TEST_PAGE).run()

    assert button_group(app, state.MANAGEMENT).value == Rebalancing.NEVER.value


def test_a_slot_is_filled_from_an_example_and_the_examples_come_back() -> None:
    app = click(run_app(DESIGN_PAGE), design.START_OWN)
    app.selectbox(key=widget_key(0, TEMPLATE)).select(CAUTIOUS.name).run()

    assert app.text_input(key=widget_key(0, NAME)).value == CAUTIOUS.name
    assert app.number_input(key=percent_key(0, "uk_gilt")).value == 60
    assert app.selectbox(key=widget_key(0, TEMPLATE)).value is None

    click(app, design.SHOW_EXAMPLES)
    names = [app.text_input(key=widget_key(index, NAME)).value for index in range(4)]
    assert names == [split.name for split in EXAMPLE_SPLITS]


def test_removing_a_holding_takes_its_box_away_and_leaves_a_gap_to_fill() -> None:
    app = run_app(DESIGN_PAGE)
    app.multiselect(key=widget_key(1, HOLDINGS)).unselect("uk_gilt").run()

    boxes = [box.key for box in app.number_input if (box.key or "").startswith("slot1.")]
    assert boxes == [percent_key(1, "ftse_all_world")]
    assert "Balanced adds up to 60%, not 100%." in captions(app)
