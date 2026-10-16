from dataclasses import replace

import pytest

from crashmodel.app import stress
from crashmodel.app.presenters import stress_test
from crashmodel.app.presenters.format import (
    month_name,
    months,
    percent,
    pounds,
    pounds_and_pence,
)
from crashmodel.app.presenters.holdings import holding_list
from crashmodel.app.splits import Slot, Split, example_slots
from crashmodel.data.french import DEVELOPED_BY_SIZE, US_BY_SIZE, Vintage
from crashmodel.data.models import IndexModel
from crashmodel.data.panel import Panel
from crashmodel.engine.episodes import COVID, EPISODES_BY_KEY, Episode
from crashmodel.engine.months import Month, MonthlySeries
from crashmodel.engine.portfolio import Rebalancing
from tests.app.example_funds import use_example_funds

EPISODE = Episode(key="test", start=Month(2007, 6), crash_end=Month(2007, 9), end=Month(2007, 10))
ALL_IN = Split(name="All in", percentages={"sp500": 100})
BONDS_ONLY = Split(name="Bonds", percentages={"uk_gilt": 100})
MODELS = {
    "us_shares": IndexModel.US_LARGE,
    "world_shares": IndexModel.DEVELOPED_LARGE,
    "gilts": IndexModel.UK_GILTS,
    "cash": IndexModel.STERLING_CASH,
}
"""The models a test panel can give returns for, by a short name."""


def in_slots(*splits: Split) -> list[Slot]:
    return [Slot(split=split) for split in splits]


def panel(**returns: tuple[float, ...]) -> Panel:
    series = {
        MODELS[name]: MonthlySeries(Month(2007, 7), values) for name, values in returns.items()
    }
    return Panel(returns=series, unavailable=frozenset(), vintages={})


def card_for(returns: tuple[float, ...], split: Split = ALL_IN) -> stress_test.CrashCard:
    [outcome] = stress.outcomes(in_slots(split), EPISODE, panel(us_shares=returns))
    return stress_test.card(outcome, EPISODE)


def test_a_fall_from_the_start_and_back_reads_as_a_story() -> None:
    card = card_for((-0.10, -0.20, 0.50, 0.0))
    assert card.sentences == (
        "All in fell 28% at worst in the crash phase.",
        "It hit bottom 2 months after the start and took another month to get back to where it "
        "started.",
        "£100 at the start was worth £108 by October 2007.",
    )


def test_a_fall_from_a_later_high_that_has_not_recovered() -> None:
    card = card_for((0.25, -0.20, -0.25, 0.0))
    assert card.sentences[1] == (
        "It hit bottom 2 months after its high and had not got back to that high by October 2007."
    )


def test_a_bottom_at_the_end_of_the_crash_phase_and_a_later_low_are_mentioned() -> None:
    still_falling = card_for((0.0, -0.10, -0.10, 0.5))
    assert (
        "still at its lowest when the crash phase ended in September 2007"
        in still_falling.sentences[2]
    )
    deeper_later = card_for((-0.05, 0.0, 0.0, -0.20))
    assert (
        deeper_later.sentences[2]
        == "After the crash phase, it fell further, to 24% below the start."
    )


def test_a_later_low_before_a_recovery_is_told_in_order() -> None:
    """Down 10% in July, down to 72 in September, after the crash phase, then back by November."""
    long = Episode(key="long", start=Month(2007, 6), crash_end=Month(2007, 8), end=Month(2007, 12))
    returns = panel(us_shares=(-0.10, 0.0, -0.20, 0.25, 0.20, 0.0))
    [outcome] = stress.outcomes(in_slots(ALL_IN), long, returns)
    assert stress_test.card(outcome, long).sentences == (
        "All in fell 10% at worst in the crash phase.",
        "It hit bottom 1 month after the start and took another 4 months to get back to where "
        "it started.",
        "After the crash phase, and before it got back, it fell further, to 28% below the start.",
        "£100 at the start was worth £108 by December 2007.",
    )


def test_a_split_that_never_fell_says_so() -> None:
    [outcome] = stress.outcomes(in_slots(BONDS_ONLY), EPISODE, panel(gilts=(0.01,) * 4))
    assert stress_test.card(outcome, EPISODE).sentences[0] == (
        "Bonds did not fall at any month end in the crash phase, to September 2007."
    )


MIXED = Split(name="Mixed", percentages={"msci_world": 50, "uk_gilt": 50})


def test_a_split_whose_data_could_not_be_fetched_says_which() -> None:
    offline = replace(panel(gilts=(0.0,) * 4), unavailable=frozenset({IndexModel.DEVELOPED_LARGE}))
    [outcome] = stress.outcomes(in_slots(MIXED), EPISODE, offline)
    assert outcome.missing == ("msci_world",)
    assert stress_test.card(outcome, EPISODE).sentences == (
        "Mixed holds MSCI World (modelled), and that data could not be fetched just now.",
    )


def test_a_split_whose_data_does_not_reach_back_far_enough_says_so() -> None:
    short = panel(gilts=(0.0,) * 4, world_shares=(0.0,) * 4)
    late = {**short.returns, IndexModel.DEVELOPED_LARGE: MonthlySeries(Month(2007, 9), (0.0, 0.0))}
    [outcome] = stress.outcomes(in_slots(MIXED), EPISODE, replace(short, returns=late))
    assert stress_test.card(outcome, EPISODE).sentences == (
        "Mixed holds MSCI World (modelled), and there is no data for every month of this crash.",
    )


def test_the_offline_banner_names_the_holdings_whose_data_failed() -> None:
    assert stress_test.offline_banner(["sp500", "msci_world"]) == (
        "The share data behind S&P 500 (modelled) and MSCI World (modelled) could not be fetched "
        "just now, so splits holding them have no results. Splits without them are not affected."
    )
    assert stress_test.offline_banner(["sp500"]).endswith(
        "so splits holding it have no results. Splits without it are not affected."
    )


def test_splits_that_do_not_add_up_are_left_out_and_slots_are_kept() -> None:
    unfinished = Split(name="Unfinished", percentages={"uk_gilt": 90})
    results = stress.outcomes(in_slots(unfinished, BONDS_ONLY), EPISODE, panel(gilts=(0.0,) * 4))
    assert [(outcome.split.name, outcome.slot) for outcome in results] == [("Bonds", 1)]


def test_table_rows_give_the_figures() -> None:
    fell = stress.outcomes(in_slots(ALL_IN), EPISODE, panel(us_shares=(-0.10, -0.20, 0.50, 0.0)))[0]
    assert stress_test.table_row(fell, EPISODE) == {
        "Split": "All in",
        "Worst fall in the crash": "28%",
        "Months to the bottom": "2",
        "Months to get back": "1",
        "£100 became": "£108",
    }
    stuck = stress.outcomes(in_slots(ALL_IN), EPISODE, panel(us_shares=(0.25, -0.2, -0.25, 0.0)))[0]
    assert stress_test.table_row(stuck, EPISODE)["Months to get back"] == "Not by October 2007"
    calm = stress.outcomes(in_slots(BONDS_ONLY), EPISODE, panel(gilts=(0.01,) * 4))[0]
    assert stress_test.table_row(calm, EPISODE)["Worst fall in the crash"] == "None"
    missing = stress.outcomes(in_slots(ALL_IN), EPISODE, panel())[0]
    assert stress_test.table_row(missing, EPISODE)["Worst fall in the crash"] == "No data"


def test_the_chart_draws_only_splits_that_could_be_run() -> None:
    results = stress.outcomes(in_slots(ALL_IN, BONDS_ONLY), EPISODE, panel(gilts=(0.0,) * 4))
    view = stress_test.chart_view(results)
    assert (view.splits, view.slots) == (("Bonds",), (1,))
    assert view.points[0] == stress_test.ChartPoint(split="Bonds", month="2007-06-01", value=100)
    assert len(view.points) == 5


def test_the_share_credit_names_each_files_update() -> None:
    vintages = {
        DEVELOPED_BY_SIZE: Vintage(month=Month(2008, 11), database="Bloomberg"),
        US_BY_SIZE: Vintage(month=Month(2008, 12), database="CRSP"),
    }
    credit = stress_test.share_credit(vintages)
    assert (
        "(US shares by size: the CRSP update of December 2008; developed markets shares by size: "
        "the Bloomberg update of November 2008)" in credit
    )
    assert "grouped by size, fetched" in stress_test.share_credit({})


@pytest.mark.parametrize(
    ("fraction", "written"),
    [(0.245, "25%"), (0.24, "24%"), (0.004, "less than 1%"), (0.0, "0%"), (1.0, "100%")],
)
def test_percentages_round_halves_up(fraction: float, written: str) -> None:
    assert percent(fraction) == written


def test_months_money_and_month_names_are_written_in_words() -> None:
    assert (months(1), months(17)) == ("1 month", "17 months")
    assert month_name(Month(2007, 6)) == "June 2007"
    assert (pounds(108.4), pounds(1234.5)) == ("£108", "£1,235")
    assert (pounds_and_pence(3.405), pounds_and_pence(0)) == ("£3.41", "£0.00")


def test_holdings_are_listed_as_in_a_sentence() -> None:
    assert holding_list(["bank_rate"]) == "Bank Rate (modelled)"
    assert holding_list(["msci_world", "sp500", "uk_gilt"]) == (
        "MSCI World (modelled), S&P 500 (modelled) and 10-year UK gilt (modelled)"
    )


def test_a_card_reads_as_one_paragraph() -> None:
    card = stress_test.CrashCard(title="Example", sentences=("One.", "Two."))
    assert card.text == "One. Two."


def test_every_crash_has_a_name_and_a_story() -> None:
    assert stress_test.episode_name(COVID.key) == "2020 Covid crash"
    assert (
        stress_test.EPISODE_NAMES.keys()
        == stress_test.EPISODE_STORIES.keys()
        == EPISODES_BY_KEY.keys()
    )


def test_the_examples_note_shows_only_while_the_splits_are_the_examples() -> None:
    assert stress_test.examples_note(example_slots()) == stress_test.EXAMPLES_NOTE
    assert stress_test.examples_note(in_slots(ALL_IN)) is None


def test_included_splits_that_do_not_add_up_are_named_as_left_out() -> None:
    over = Split(name="Over", percentages={"bank_rate": 105})
    slots = [Slot(split=over), Slot(split=over, included=False), Slot(split=BONDS_ONLY)]
    assert stress_test.left_out_note(slots) == (
        "Over is left out, because it adds up to 105%, not 100%."
    )
    assert stress_test.left_out_note(in_slots(BONDS_ONLY)) is None


def test_splits_switched_off_are_not_run() -> None:
    slots = [Slot(split=ALL_IN, included=False), Slot(split=BONDS_ONLY)]
    results = stress.outcomes(slots, EPISODE, panel(gilts=(0.0,) * 4))
    assert [(outcome.split.name, outcome.slot) for outcome in results] == [("Bonds", 1)]


def test_typed_names_are_escaped_in_words_and_table_but_not_on_the_chart() -> None:
    starred = Split(name="*Mine*", percentages={"uk_gilt": 100})
    [outcome] = stress.outcomes(in_slots(starred), EPISODE, panel(gilts=(0.0,) * 4))
    assert stress_test.card(outcome, EPISODE).title == r"\*Mine\*"
    assert stress_test.table_row(outcome, EPISODE)["Split"] == r"\*Mine\*"
    assert stress_test.chart_view([outcome]).splits == ("*Mine*",)


def test_the_why_says_what_each_holding_lost_or_made_back_per_100_at_the_start() -> None:
    mixed = Split(name="Mixed", percentages={"sp500": 60, "uk_gilt": 40})
    returns = panel(us_shares=(-0.40, 0.0, 0.0, 0.0), gilts=(0.10, 0.0, 0.0, 0.0))
    [outcome] = stress.outcomes(in_slots(mixed), EPISODE, returns)
    assert stress_test.card(outcome, EPISODE).why == (
        "Of every £100 it had at the start, S&P 500 (modelled) lost £24.00 and 10-year UK gilt "
        "(modelled) made back £4.00 on the way down to its low in the crash phase.",
    )


def test_a_split_of_one_holding_needs_no_breakdown_of_its_fall() -> None:
    assert card_for((-0.10, -0.20, 0.50, 0.0)).why == ()


def with_dollars(pounds: tuple[float, ...], dollars: tuple[float, ...]) -> Panel:
    start = Month(2007, 7)
    return Panel(
        returns={IndexModel.US_LARGE: MonthlySeries(start, pounds)},
        unavailable=frozenset(),
        vintages={},
        dollar_returns={IndexModel.US_LARGE: MonthlySeries(start, dollars)},
    )


IN_DOLLARS = "With its shares' returns counted in dollars rather than pounds, it would"


@pytest.mark.parametrize(
    ("in_pounds", "in_dollars", "sentence"),
    [
        (
            -0.10,
            -0.25,
            f"{IN_DOLLARS} have fallen 25% at worst in the crash phase rather than 10%: "
            "the pound's moves against the dollar cushioned it.",
        ),
        (
            -0.25,
            -0.10,
            f"{IN_DOLLARS} have fallen 10% at worst in the crash phase rather than 25%: "
            "the pound's moves against the dollar made it worse.",
        ),
        (
            -0.10,
            0.00,
            f"{IN_DOLLARS} not have fallen in the crash phase: the pound's moves against the "
            "dollar made it worse.",
        ),
        (
            0.01,
            -0.10,
            f"{IN_DOLLARS} have fallen 10% at worst in the crash phase: the pound's moves "
            "against the dollar cushioned it.",
        ),
    ],
)
def test_the_why_says_what_the_pound_did(
    in_pounds: float, in_dollars: float, sentence: str
) -> None:
    returns = with_dollars((in_pounds, 0.0, 0.0, 0.0), (in_dollars, 0.0, 0.0, 0.0))
    [outcome] = stress.outcomes(in_slots(ALL_IN), EPISODE, returns)
    assert stress_test.card(outcome, EPISODE).why == (sentence,)


def test_the_pound_is_not_mentioned_when_it_made_no_visible_difference() -> None:
    returns = with_dollars((-0.100, 0.0, 0.0, 0.0), (-0.101, 0.0, 0.0, 0.0))
    [outcome] = stress.outcomes(in_slots(ALL_IN), EPISODE, returns)
    assert stress_test.card(outcome, EPISODE).why == ()


def test_each_way_of_managing_a_split_has_a_name() -> None:
    assert stress_test.management_name(Rebalancing.NEVER.value) == "Left alone"
    assert set(stress_test.MANAGEMENT_NAMES) == {rebalancing.value for rebalancing in Rebalancing}


def test_a_fall_too_small_to_show_in_pence_needs_no_breakdown() -> None:
    tiny = Split(name="Tiny", percentages={"sp500": 50, "uk_gilt": 50})
    returns = panel(us_shares=(-0.00002, 0.0, 0.0, 0.0), gilts=(0.0,) * 4)
    [outcome] = stress.outcomes(in_slots(tiny), EPISODE, returns)
    assert outcome.run is not None
    assert outcome.run.result.fall is not None
    assert stress_test.card(outcome, EPISODE).why == ()


def test_a_fall_is_never_put_down_to_gains_alone() -> None:
    """Two holdings lose less than half a penny each per £100, while cash makes back a penny."""
    mixed = Split(
        name="Mixed",
        percentages={"msci_world": 20, "uk_gilt": 60, "bank_rate": 20},
    )
    returns = panel(
        world_shares=(-0.0002, 0.0, 0.0, 0.0),
        gilts=(-0.00005, 0.0, 0.0, 0.0),
        cash=(0.0003, 0.0, 0.0, 0.0),
    )
    [outcome] = stress.outcomes(in_slots(mixed), EPISODE, returns)
    assert outcome.run is not None
    assert outcome.run.result.fall is not None
    assert stress_test.card(outcome, EPISODE).why == ()


@pytest.fixture
def example_funds(monkeypatch: pytest.MonkeyPatch) -> None:
    use_example_funds(monkeypatch)


@pytest.mark.usefixtures("example_funds")
def test_a_fund_launched_after_the_crash_began_is_named_with_its_launch() -> None:
    split = Split(name="Late", percentages={"late": 50, "sp500": 50})
    [outcome] = stress.outcomes(in_slots(split), EPISODE, panel(us_shares=(0.0,) * 4))
    assert stress_test.card(outcome, EPISODE).notes_text == (
        "LATE was launched after this crash began, in August 2007. Its figures, like every figure "
        "here, come from a model of the index it tracks, after its charge."
    )


@pytest.mark.usefixtures("example_funds")
def test_funds_launched_after_the_crash_began_share_one_note() -> None:
    split = Split(name="Late", percentages={"late": 40, "sp500": 20, "later": 40})
    [outcome] = stress.outcomes(in_slots(split), EPISODE, panel(us_shares=(0.0,) * 4))
    assert stress_test.card(outcome, EPISODE).notes_text == (
        "LATE and LATER were launched after this crash began, in August 2007 and September 2007. "
        "Their figures, like every figure here, come from models of the indexes they track, after "
        "their charges."
    )


@pytest.mark.usefixtures("example_funds")
def test_no_note_for_funds_that_already_existed_or_are_held_at_nothing() -> None:
    split = Split(name="Held", percentages={"early": 50, "start": 50, "late": 0})
    [outcome] = stress.outcomes(in_slots(split), EPISODE, panel(us_shares=(0.0,) * 4))
    assert stress_test.card(outcome, EPISODE).notes == ()
