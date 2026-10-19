from crashmodel.app.presenters import how_it_works
from tests.app.running import ROOT

REPOSITORY = "https://github.com/example/project"


def test_the_reasons_link_each_decision_record_and_the_about_section_links_the_code() -> None:
    text = " ".join(
        paragraph
        for section in how_it_works.sections(REPOSITORY)
        for paragraph in section.paragraphs
    )
    for _, name in how_it_works.DECISION_RECORDS:
        assert f"]({REPOSITORY}/blob/main/docs/decisions/{name})" in text
    assert f"[the code]({REPOSITORY})" in text


def test_without_a_repository_the_page_makes_no_links_to_it() -> None:
    sections = how_it_works.sections(None)
    text = " ".join(paragraph for section in sections for paragraph in section.paragraphs)
    assert "github" not in text.casefold()
    assert "decision records stored with the code" in text


def test_the_page_says_what_the_models_leave_out_and_that_it_is_not_advice() -> None:
    limits = " ".join(how_it_works.LIMITS.paragraphs)
    assert "simulated" in limits
    assert "not a reliable indicator of future results" in limits
    assert "nothing in this app is investment advice" in limits


def test_each_linked_decision_record_exists() -> None:
    for _, name in how_it_works.DECISION_RECORDS:
        assert (ROOT / "docs/decisions" / name).is_file(), name
