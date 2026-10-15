import pytest

from crashmodel.app.presenters import stress_test
from crashmodel.app.presenters.blocks import block_list
from crashmodel.app.presenters.format import month_name, months, percent, pounds
from crashmodel.app.splits import Split
from crashmodel.data.blocks import Block
from crashmodel.data.french import Vintage
from crashmodel.data.panel import Panel
from crashmodel.engine.episodes import COVID, EPISODES_BY_KEY, Episode
from crashmodel.engine.months import Month, MonthlySeries

EPISODE = Episode(key="test", start=Month(2007, 6), crash_end=Month(2007, 9), end=Month(2007, 10))
ALL_IN = Split(name="All in", percentages={Block.US_SHARES: 100})
SAFE_AS = Split(name="Bonds", percentages={Block.UK_BONDS: 100})


def panel(**returns: tuple[float, ...]) -> Panel:
    series = {
        Block(name): MonthlySeries(Month(2007, 7), values) for name, values in returns.items()
    }
    return Panel(returns=series, unavailable=frozenset(), vintages={})


def card_for(returns: tuple[float, ...], split: Split = ALL_IN) -> stress_test.CrashCard:
    [outcome] = stress_test.outcomes([split], EPISODE, panel(us_shares=returns))
    return stress_test.card(outcome, EPISODE)


def test_a_fall_from_the_start_and_back_reads_as_a_story() -> None:
    card = card_for((-0.10, -0.20, 0.50, 0.0))
    assert card.sentences == (
        "All in fell 28% at worst.",
        "It hit bottom 2 months after the start and took another 1 month to get back to where "
        "it started.",
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
    assert deeper_later.sentences[2] == "It later fell further, to 24% below the start."


def test_a_split_that_never_fell_says_so() -> None:
    [outcome] = stress_test.outcomes([SAFE_AS], EPISODE, panel(uk_bonds=(0.01,) * 4))
    assert stress_test.card(outcome, EPISODE).sentences[0] == (
        "Bonds did not fall at any month end during the crash."
    )


def test_a_split_whose_data_is_unavailable_says_which() -> None:
    mixed = Split(name="Mixed", percentages={Block.GLOBAL_SHARES: 50, Block.UK_BONDS: 50})
    [outcome] = stress_test.outcomes([mixed], EPISODE, panel(uk_bonds=(0.0,) * 4))
    assert outcome.missing == (Block.GLOBAL_SHARES,)
    assert stress_test.card(outcome, EPISODE).sentences == (
        "Mixed holds global shares, and that data could not be fetched just now.",
    )


def test_splits_that_do_not_add_up_are_left_out_and_slots_are_kept() -> None:
    unfinished = Split(name="Unfinished", percentages={Block.UK_BONDS: 90})
    results = stress_test.outcomes([unfinished, SAFE_AS], EPISODE, panel(uk_bonds=(0.0,) * 4))
    assert [(outcome.split.name, outcome.slot) for outcome in results] == [("Bonds", 1)]


def test_table_rows_give_the_figures() -> None:
    fell = stress_test.outcomes([ALL_IN], EPISODE, panel(us_shares=(-0.10, -0.20, 0.50, 0.0)))[0]
    assert stress_test.table_row(fell, EPISODE) == {
        "Split": "All in",
        "Worst fall": "28%",
        "Months to the bottom": "2",
        "Months to get back": "1",
        "£100 became": "£108",
    }
    stuck = stress_test.outcomes([ALL_IN], EPISODE, panel(us_shares=(0.25, -0.2, -0.25, 0.0)))[0]
    assert stress_test.table_row(stuck, EPISODE)["Months to get back"] == "Not by October 2007"
    calm = stress_test.outcomes([SAFE_AS], EPISODE, panel(uk_bonds=(0.01,) * 4))[0]
    assert stress_test.table_row(calm, EPISODE)["Worst fall"] == "Did not fall"
    missing = stress_test.outcomes([ALL_IN], EPISODE, panel())[0]
    assert stress_test.table_row(missing, EPISODE)["Worst fall"] == "No data"


def test_the_chart_draws_only_splits_that_could_be_run() -> None:
    results = stress_test.outcomes([ALL_IN, SAFE_AS], EPISODE, panel(uk_bonds=(0.0,) * 4))
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
    card = stress_test.CrashCard(title="Example", slot=0, sentences=("One.", "Two."))
    assert card.text == "One. Two."


def test_every_crash_has_a_name_and_a_story() -> None:
    assert stress_test.episode_name(COVID.key) == "2020 Covid crash"
    assert (
        stress_test.EPISODE_NAMES.keys()
        == stress_test.EPISODE_STORIES.keys()
        == EPISODES_BY_KEY.keys()
    )
