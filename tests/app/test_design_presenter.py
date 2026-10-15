import pytest

from crashmodel.app.journey import DESIGN
from crashmodel.app.presenters import design
from crashmodel.app.presenters.names import display_names, markdown_text
from crashmodel.app.presenters.progress import progress
from crashmodel.app.splits import Slot, Split, empty_slots, example_slots
from crashmodel.data.blocks import Block


def slot(name: str = "Mine", *, included: bool = True, cash: int = 0, bonds: int = 0) -> Slot:
    percentages = {Block.CASH: cash, Block.UK_BONDS: bonds}
    return Slot(split=Split(name=name, percentages=percentages), included=included)


@pytest.mark.parametrize(
    ("cash", "bonds", "text", "colour"),
    [
        (100, 0, "Adds up to 100%", "green"),
        (60, 45, "Adds up to 105%: take 5 off", "orange"),
        (90, 0, "Adds up to 90%: add 10 more", "orange"),
        (0, 0, "Adds up to 0%: add 100 more", "orange"),
    ],
)
def test_the_badge_says_what_a_split_adds_up_to_and_what_to_change(
    cash: int, bonds: int, text: str, colour: str
) -> None:
    badge = design.total_badge(slot(cash=cash, bonds=bonds))
    assert (badge.text, badge.colour) == (text, colour)


def test_a_left_out_split_has_a_grey_badge_whatever_it_adds_up_to() -> None:
    badge = design.total_badge(slot(included=False, cash=40))
    assert (badge.text, badge.colour) == ("Left out", "gray")


def test_the_examples_are_ready_to_test() -> None:
    assert design.next_blocker(example_slots()) is None


def test_every_included_split_must_add_up_to_100() -> None:
    slots = [slot(cash=100), slot("Too much", cash=105), slot("Ignored", included=False)]
    assert design.next_blocker(slots) == "Too much adds up to 105%, not 100%."


def test_at_least_one_split_must_be_included() -> None:
    slots = [slot(included=False, cash=100)] * 4
    assert design.next_blocker(slots) == design.NOTHING_INCLUDED


def test_each_box_is_labelled_with_its_block_and_unit() -> None:
    assert design.block_label(Block.UK_BONDS) == "UK government bonds (%)"


def test_blank_names_take_their_place_and_repeats_among_included_splits_are_numbered() -> None:
    slots = [slot("Mine"), slot("  "), slot("Mine"), slot("Mine", included=False)]
    assert display_names(slots) == ("Mine", "Split 2", "Mine (2)", "Mine")


def test_a_number_never_clashes_with_a_name_the_visitor_typed() -> None:
    slots = [slot("Mine"), slot("Mine (2)"), slot("Mine")]
    assert display_names(slots) == ("Mine", "Mine (2)", "Mine (3)")


def test_empty_slots_are_named_by_their_place() -> None:
    assert display_names(empty_slots()) == ("Split 1", "Split 2", "Split 3", "Split 4")


@pytest.mark.parametrize(
    ("typed", "escaped"),
    [
        ("Plain name", "Plain name"),
        ("**bold**", r"\*\*bold\*\*"),
        ("[link](x)", r"\[link\]\(x\)"),
        (":red[alarm]", r"\:red\[alarm\]"),
        ("$x$ # 1. <b>", r"\$x\$ \# 1\. \<b\>"),
    ],
)
def test_typed_names_are_shown_exactly_as_typed(typed: str, escaped: str) -> None:
    assert markdown_text(typed) == escaped


def test_the_composition_shows_each_included_splits_blocks_in_their_usual_order() -> None:
    slots = [slot("Mine", cash=40, bonds=60), slot("Off", included=False, cash=100)]
    view = design.composition_view(slots)
    assert view.splits == ("Mine",)
    assert [(point.block, point.percent, point.order) for point in view.points] == [
        ("UK government bonds", 60, 2),
        ("Cash", 40, 3),
    ]


def test_each_journey_page_says_which_step_it_is() -> None:
    step = progress(DESIGN)
    assert (step.fraction, step.text) == (0.25, "Step 1 of 4: Design")
