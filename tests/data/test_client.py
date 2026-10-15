from crashmodel import __version__
from crashmodel.data.client import CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS, make_client


def test_the_client_identifies_the_project_without_personal_details() -> None:
    with make_client() as client:
        agent = client.headers["User-Agent"]

    assert agent.startswith(f"crashmodel/{__version__}")
    assert "@" not in agent


def test_the_client_gives_up_quickly_on_a_silent_server() -> None:
    with make_client() as client:
        assert client.timeout.connect == CONNECT_TIMEOUT_SECONDS
        assert client.timeout.read == READ_TIMEOUT_SECONDS
        assert client.follow_redirects
