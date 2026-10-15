from dataclasses import replace

import pytest

from crashmodel.app.presenters import stress_test
from crashmodel.app.presenters.blocks import block_list
from crashmodel.app.presenters.format import month_name, months, percent, pounds
from crashmodel.app.splits import Slot, Split, example_slots
from crashmodel.data.blocks import Block
from crashmodel.data.french import Vintage
from crashmodel.data.panel import Panel
from crashmodel.engine.episodes import COVID, EPISODES_BY_KEY, Episode
from crashmodel.engine.months import Month, MonthlySeries

EPISODE = Episode(key="test", start=Month(2007, 6), crash_end=Month(2007, 9), end=Month(2007, 10))
ALL_IN = Split(name="All in", percentages={Block.US_SHARES: 100})
BONDS_ONLY = Split(name="Bonds", percentages={Block.UK_BONDS: 100})


def in_slots(*splits: Split) -> list[Slot]:
    return [Slot(split=split) for split in splits]


def panel(**returns: tuple[float, ...]) -> Panel:
    series = {
        Block(name): MonthlySeries(Month(2007, 7), values) for name, values in returns.items()
    }
    return Panel(returns=series, unavailable=frozenset(), vintages={})


def card_for(returns: tuple[float, ...], split: Split = ALL_IN) -> stress_test.CrashCard:
    [outcome] = stress_test.outcomes(in_slots(split), EPISODE, panel(us_shares=returns))
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
    [outcome] = stress_test.outcomes(in_slots(ALL_IN), long, returns)
    assert stress_test.card(outcome, long).sentences == (
        "All in fell 10% at worst in the crash phase.",
        "It hit bottom 1 month after the start and took another 4 months to get back to where "
        "it started.",
        "After the crash phase, and before it got back, it fell further, to 28% below the start.",
        "£100 at the start was worth £108 by December 2007.",
    )


def test_a_split_that_never_fell_says_so() -> None:
    [outcome] = stress_test.outcomes(in_slots(BONDS_ONLY), EPISODE, panel(uk_bonds=(0.01,) * 4))
    assert stress_test.card(outcome, EPISODE).sentences[0] == (
        "Bonds did not fall at any month end in the crash phase, to September 2007."
    )


MIXED = Split(name="Mixed", percentages={Block.GLOBAL_SHARES: 50, Block.UK_BONDS: 50})


def test_a_split_whose_data_could_not_be_fetched_says_which() -> None:
    offline = replace(panel(uk_bonds=(0.0,) * 4), unavailable=frozenset({Block.GLOBAL_SHARES}))
    [outcome] = stress_test.outcomes(in_slots(MIXED), EPISODE, offline)
    assert outcome.missing == (Block.GLOBAL_SHARES,)
    assert stress_test.card(outcome, EPISODE).sentences == (
        "Mixed holds global shares, and that data could not be fetched just now.",
    )


def test_a_split_whose_data_does_not_reach_back_far_enough_says_so() -> None:
    short = panel(uk_bonds=(0.0,) * 4, global_shares=(0.0,) * 4)
    late = {**short.returns, Block.GLOBAL_SHARES: MonthlySeries(Month(2007, 9), (0.0, 0.0))}
    [outcome] = stress_test.outcomes(in_slots(MIXED), EPISODE, replace(short, returns=late))
    assert stress_test.card(outcome, EPISODE).sentences == (
        "Mixed holds global shares, and there is no data for every month of this crash.",
    )


def test_the_offline_banner_names_only_the_blocks_that_failed() -> None:
    banner = stress_test.offline_banner({Block.US_SHARES})
    assert banner.startswith("Returns on US shares could not be fetched just now")


def test_splits_that_do_not_add_up_are_left_out_and_slots_are_kept() -> None:
    unfinished = Split(name="Unfinished", percentages={Block.UK_BONDS: 90})
    results = stress_test.outcomes(
        in_slots(unfinished, BONDS_ONLY), EPISODE, panel(uk_bonds=(0.0,) * 4)
    )
    assert [(outcome.split.name, outcome.slot) for outcome in results] == [("Bonds", 1)]


def test_table_rows_give_the_figures() -> None:
    fell = stress_test.outcomes(
        in_slots(ALL_IN), EPISODE, panel(us_shares=(-0.10, -0.20, 0.50, 0.0))
    )[0]
    assert stress_test.table_row(fell, EPISODE) == {
        "Split": "All in",
        "Worst fall in the crash": "28%",
        "Months to the bottom": "2",
        "Months to get back": "1",
        "£100 became": "£108",
    }
    stuck = stress_test.outcomes(
        in_slots(ALL_IN), EPISODE, panel(us_shares=(0.25, -0.2, -0.25, 0.0))
    )[0]
    assert stress_test.table_row(stuck, EPISODE)["Months to get back"] == "Not by October 2007"
    calm = stress_test.outcomes(in_slots(BONDS_ONLY), EPISODE, panel(uk_bonds=(0.01,) * 4))[0]
    assert stress_test.table_row(calm, EPISODE)["Worst fall in the crash"] == "None"
    missing = stress_test.outcomes(in_slots(ALL_IN), EPISODE, panel())[0]
    assert stress_test.table_row(missing, EPISODE)["Worst fall in the crash"] == "No data"


def test_the_chart_draws_only_splits_that_could_be_run() -> None:
    results = stress_test.outcomes(
        in_slots(ALL_IN, BONDS_ONLY), EPISODE, panel(uk_bonds=(0.0,) * 4)
    )
    view = stress_test.chart_view(results)
    assert (view.splits, view.slots) == (("Bonds",), (1,))
    assert view.points[0] == stress_test.ChartPoint(split="Bonds", month="2007-06-01", value=100)
    assert len(view.points) == 5


def test_the_share_credit_names_each_files_update() -> None:
    vintages = {
        Block.US_SHARES: Vintage(month=Month(2008, 12), database="CRSP"),
        Block.GLOBAL_SHARES: Vintage(month=Month(2008, 11), database="Bloomberg"),
    }
    credit = stress_test.share_credit(vintages)
    assert (
        "(global shares: the Bloomberg update of November 2008; US shares: the CRSP update"
        in credit
    )
    assert "Kenneth R. French Data Library, fetched" in stress_test.share_credit({})


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


def test_blocks_are_listed_as_in_a_sentence() -> None:
    assert block_list([Block.CASH]) == "cash"
    assert block_list([Block.GLOBAL_SHARES, Block.US_SHARES, Block.UK_BONDS]) == (
        "global shares, US shares and UK government bonds"
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
    over = Split(name="Over", percentages={Block.CASH: 105})
    slots = [Slot(split=over), Slot(split=over, included=False), Slot(split=BONDS_ONLY)]
    assert stress_test.left_out_note(slots) == (
        "Over is left out, because it adds up to 105%, not 100%."
    )
    assert stress_test.left_out_note(in_slots(BONDS_ONLY)) is None


def test_splits_switched_off_are_not_run() -> None:
    slots = [Slot(split=ALL_IN, included=False), Slot(split=BONDS_ONLY)]
    results = stress_test.outcomes(slots, EPISODE, panel(uk_bonds=(0.0,) * 4))
    assert [(outcome.split.name, outcome.slot) for outcome in results] == [("Bonds", 1)]


def test_typed_names_are_escaped_in_words_and_table_but_not_on_the_chart() -> None:
    starred = Split(name="*Mine*", percentages={Block.UK_BONDS: 100})
    [outcome] = stress_test.outcomes(in_slots(starred), EPISODE, panel(uk_bonds=(0.0,) * 4))
    assert stress_test.card(outcome, EPISODE).title == r"\*Mine\*"
    assert stress_test.table_row(outcome, EPISODE)["Split"] == r"\*Mine\*"
    assert stress_test.chart_view([outcome]).splits == ("*Mine*",)
