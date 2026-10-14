from pathlib import Path

import pytest

from tests.tools.helpers import GitRunner, png, png_chunk
from tests.tools.sentinels import NAME_LINE, TICKER_LINE
from tools import privacy_scan as scan
from tools._report import EXIT_CLEAN, EXIT_CONFIG_ERROR, EXIT_PROBLEMS
from tools.denylist import parse_entry


def commit_file(run_git: GitRunner, repo: Path, name: str, content: bytes) -> None:
    (repo / name).write_bytes(content)
    run_git("add", "-f", name)
    run_git("commit", "-q", "--no-verify", "-m", f"Add {name}")


def push_scan(denylist: Path, remote: str = "origin") -> int:
    return scan.main(["--push", "--remote", remote, "--denylist", str(denylist)])


def test_staged_scan_reports_location_and_entry_without_echoing_the_match(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "notes.md").write_text("Fine line\nOwner: Zebedee Quartermaine\n", encoding="utf-8")
    run_git("add", "notes.md")

    exit_code = scan.main(["--staged", "--denylist", str(denylist)])

    output = capsys.readouterr().err
    assert exit_code == EXIT_PROBLEMS
    assert f"notes.md:2: matches denylist line {NAME_LINE}" in output
    assert "zebedee" not in output.lower()
    assert "quartermaine" not in output.lower()


def test_staged_scan_checks_file_names(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "zqxw_prices.csv").write_text("date,price\n", encoding="utf-8")
    run_git("add", "zqxw_prices.csv")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS
    output = capsys.readouterr().err
    assert f"<name hidden>: file name matches denylist line {TICKER_LINE}" in output
    assert "zqxw" not in output.lower()


def test_staged_scan_blocks_binary_data_formats(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "portfolio.xlsx").write_bytes(b"PK\x03\x04\x00binary")
    run_git("add", "portfolio.xlsx")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS
    assert "binary data formats are never committed" in capsys.readouterr().err


def test_staged_scan_passes_clean_changes(repo: Path, run_git: GitRunner, denylist: Path) -> None:
    (repo / "README.md").write_text("A demo portfolio of 60% shares.\n", encoding="utf-8")
    run_git("add", "README.md")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_CLEAN


@pytest.mark.usefixtures("repo")
def test_scan_fails_closed_without_a_denylist(tmp_path: Path) -> None:
    missing = tmp_path / "nowhere" / "denylist.txt"
    assert scan.main(["--staged", "--denylist", str(missing)]) == EXIT_CONFIG_ERROR


@pytest.mark.usefixtures("repo")
def test_scan_treats_a_malformed_denylist_as_a_configuration_error(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.txt"
    malformed.write_text("2031-02-30\n", encoding="utf-8")
    assert scan.main(["--staged", "--denylist", str(malformed)]) == EXIT_CONFIG_ERROR


@pytest.mark.usefixtures("repo")
def test_message_scan_checks_the_commit_message(tmp_path: Path, denylist: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("Add ZQXW prices\n", encoding="utf-8")

    assert scan.main(["--message", str(message), "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_history_scan_checks_commit_authors(repo: Path, run_git: GitRunner, denylist: Path) -> None:
    (repo / "a.txt").write_text("clean\n", encoding="utf-8")
    run_git("add", "a.txt")
    run_git("commit", "-q", "-m", "Clean message", env={"GIT_AUTHOR_NAME": "Zebedee Quartermaine"})

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_push_scan_checks_commits_that_the_remote_does_not_have(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    commit_file(run_git, repo, "a.txt", b"unit count 314.159\n")

    assert push_scan(denylist) == EXIT_PROBLEMS


def test_push_scan_skips_commits_the_remote_already_has(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    commit_file(run_git, repo, "a.txt", b"unit count 314.159\n")
    run_git("update-ref", "refs/remotes/origin/main", "HEAD")

    assert push_scan(denylist) == EXIT_CLEAN


def test_push_scan_covers_branches_other_than_the_one_checked_out(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    commit_file(run_git, repo, "a.txt", b"Owner: Zebedee Quartermaine\n")
    run_git("switch", "-q", "--orphan", "tidy")
    commit_file(run_git, repo, "b.txt", b"clean\n")

    assert push_scan(denylist) == EXIT_PROBLEMS


def test_push_scan_covers_every_branch_in_a_push_of_several(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    commit_file(run_git, repo, "a.txt", b"clean\n")
    run_git("update-ref", "refs/remotes/origin/main", "HEAD")
    run_git("switch", "-q", "-c", "feature")
    commit_file(run_git, repo, "b.txt", b"Owner: Zebedee Quartermaine\n")
    run_git("switch", "-q", "main")

    assert push_scan(denylist) == EXIT_PROBLEMS


def test_push_scan_rescans_commits_that_only_another_remote_has(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    commit_file(run_git, repo, "a.txt", b"Owner: Zebedee Quartermaine\n")
    run_git("update-ref", "refs/remotes/backup/main", "HEAD")

    assert push_scan(denylist, remote="origin") == EXIT_PROBLEMS
    assert push_scan(denylist, remote="backup") == EXIT_CLEAN


@pytest.mark.usefixtures("repo")
def test_push_scan_refuses_to_guess_the_remote(
    denylist: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PRE_COMMIT_REMOTE_NAME", raising=False)

    with pytest.raises(SystemExit) as raised:
        scan.main(["--push", "--denylist", str(denylist)])

    assert raised.value.code == EXIT_CONFIG_ERROR


def test_push_scan_takes_the_remote_from_pre_commit(
    repo: Path, run_git: GitRunner, denylist: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit_file(run_git, repo, "a.txt", b"clean\n")
    monkeypatch.setenv("PRE_COMMIT_REMOTE_NAME", "origin")

    assert scan.main(["--push", "--denylist", str(denylist)]) == EXIT_CLEAN


def test_screenshots_get_a_note_but_other_binaries_are_refused(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "docs" / "img").mkdir(parents=True)
    (repo / "docs" / "img" / "home.png").write_bytes(png())
    (repo / "blob.bin").write_bytes(b"\x00\x01binary")
    run_git("add", "docs/img/home.png", "blob.bin")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS
    output = capsys.readouterr().err
    assert "note: docs/img/home.png: screenshot pixels cannot be scanned" in output
    assert "blob.bin: binary file cannot be scanned" in output


def test_a_clean_screenshot_passes_with_a_note(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    (repo / "docs" / "img").mkdir(parents=True)
    (repo / "docs" / "img" / "home.png").write_bytes(png())
    run_git("add", "docs/img/home.png")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_CLEAN


@pytest.mark.parametrize(
    "content",
    [b"PK\x03\x04\x00\x00 an archive", png(png_chunk(b"tEXt", b"Author\x00Someone"))],
    ids=["renamed archive", "metadata"],
)
def test_screenshots_that_are_not_clean_pngs_are_refused(
    repo: Path, run_git: GitRunner, denylist: Path, content: bytes
) -> None:
    (repo / "docs" / "img").mkdir(parents=True)
    (repo / "docs" / "img" / "chart.png").write_bytes(content)
    run_git("add", "docs/img/chart.png")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS


@pytest.mark.usefixtures("repo")
def test_short_entries_trigger_a_false_positive_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "short.txt"
    path.write_text("AB\n", encoding="utf-8")

    assert scan.main(["--staged", "--denylist", str(path)]) == EXIT_CLEAN
    assert "denylist line 1 is short" in capsys.readouterr().err


def test_staged_scan_reads_a_file_that_replaces_a_symbolic_link(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    (repo / "notes.md").symlink_to("elsewhere.md")
    run_git("add", "notes.md")
    run_git("commit", "-q", "-m", "Add a link")
    (repo / "notes.md").unlink()
    (repo / "notes.md").write_text("Owner: Zebedee Quartermaine\n", encoding="utf-8")
    run_git("add", "notes.md")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_staged_scan_reads_the_target_of_a_symbolic_link(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    (repo / "notes.md").symlink_to("Zebedee Quartermaine.md")
    run_git("add", "notes.md")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_staged_scan_reads_files_whose_names_look_like_index_stages(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    (repo / "notes.md").write_text("clean\n", encoding="utf-8")
    (repo / "0:notes.md").write_text("Owner: Zebedee Quartermaine\n", encoding="utf-8")
    run_git("add", "notes.md", "0:notes.md")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS


@pytest.mark.parametrize(
    ("attributes_file", "attributes"),
    [(".gitattributes", "*.csv -diff\n"), (".git/info/attributes", "*.csv binary\n")],
)
def test_history_scan_ignores_attributes_that_hide_diffs(
    repo: Path, run_git: GitRunner, denylist: Path, attributes_file: str, attributes: str
) -> None:
    (repo / attributes_file).write_text(attributes, encoding="utf-8")
    commit_file(run_git, repo, "holdings.csv", b"name,value\nZebedee Quartermaine,1\n")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_history_scan_ignores_text_conversion_drivers(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    run_git("config", "diff.blank.textconv", "sed d")
    (repo / ".git" / "info" / "attributes").write_text("*.csv diff=blank\n", encoding="utf-8")
    commit_file(run_git, repo, "holdings.csv", b"name,value\nZebedee Quartermaine,1\n")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_history_scan_reads_the_root_commit_whatever_the_log_settings(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    run_git("config", "log.showRoot", "false")
    commit_file(run_git, repo, "notes.md", b"Owner: Zebedee Quartermaine\n")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_history_scan_catches_a_workbook_that_a_later_commit_deleted(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_file(run_git, repo, "portfolio.xlsx", b"PK\x03\x04\x00binary")
    run_git("rm", "-q", "portfolio.xlsx")
    run_git("commit", "-q", "-m", "Remove the workbook")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS
    assert "portfolio.xlsx: binary data formats are never committed" in capsys.readouterr().err


def test_history_scan_checks_every_name_given_to_the_same_content(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    commit_file(run_git, repo, "clean.csv", b"date,price\n")
    commit_file(run_git, repo, "zqxw_prices.csv", b"date,price\n")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_history_scan_matches_file_names_that_are_not_ascii(
    repo: Path, run_git: GitRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    denylist = tmp_path / "accented.txt"
    denylist.write_text("Zoë\n", encoding="utf-8")
    commit_file(run_git, repo, "zoë_notes.txt", b"clean\n")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS
    assert "file name matches denylist line 1" in capsys.readouterr().err


def test_history_scan_checks_annotated_tag_messages(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    commit_file(run_git, repo, "a.txt", b"clean\n")
    run_git("tag", "-a", "v1", "-m", "Release for ZQXW")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_history_scan_checks_branch_names(repo: Path, run_git: GitRunner, denylist: Path) -> None:
    commit_file(run_git, repo, "a.txt", b"clean\n")
    run_git("branch", "zqxw-research")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS


def test_commit_ids_are_never_checked_as_file_names() -> None:
    entries = [parse_entry(1, "AB"), parse_entry(2, "4096")]
    documents = [scan.Document(b"clean", "commit 3ab12cd04096")]

    assert scan.scan_documents(documents, entries) == []


def test_clean_history_passes(repo: Path, run_git: GitRunner, denylist: Path) -> None:
    commit_file(run_git, repo, "a.txt", b"A demo split of 60% shares.\n")
    run_git("tag", "-a", "v1", "-m", "First release")
    run_git("tag", "lightweight")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_CLEAN


def test_history_scan_reports_content_that_returns_unchanged_once(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_file(run_git, repo, "notes.md", b"Owner: Zebedee Quartermaine\n")
    commit_file(run_git, repo, "notes.md", b"clean\n")
    commit_file(run_git, repo, "notes.md", b"Owner: Zebedee Quartermaine\n")

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == EXIT_PROBLEMS
    assert "1 problem(s) found" in capsys.readouterr().err


LOCK_LINE = 'wheels = [{ hash = "sha256:9f271828e0", upload-time = "2031-02-17T09:30:00Z" }]\n'


def test_the_lock_file_is_scanned_for_words_but_not_numbers(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    (repo / "uv.lock").write_text(LOCK_LINE, encoding="utf-8")
    run_git("add", "uv.lock")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_CLEAN

    (repo / "uv.lock").write_text(LOCK_LINE + 'name = "zqxw"\n', encoding="utf-8")
    run_git("add", "uv.lock")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS


@pytest.mark.parametrize("path", ["notes.md", "docs/uv.lock"])
def test_numbers_in_any_other_file_are_still_scanned(
    repo: Path, run_git: GitRunner, denylist: Path, path: str
) -> None:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(LOCK_LINE, encoding="utf-8")
    run_git("add", path)

    assert scan.main(["--staged", "--denylist", str(denylist)]) == EXIT_PROBLEMS
