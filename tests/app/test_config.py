"""The Streamlit settings a public app depends on."""

import tomllib
from pathlib import Path

CONFIG = Path(__file__).parents[2] / ".streamlit/config.toml"


def test_a_public_visitor_never_sees_a_traceback_or_the_developer_menu() -> None:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["client"] == {"showErrorDetails": "type", "toolbarMode": "viewer"}


def test_pages_draw_only_what_they_ask_for_and_local_runs_send_no_statistics() -> None:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["runner"]["magicEnabled"] is False
    assert config["browser"]["gatherUsageStats"] is False
