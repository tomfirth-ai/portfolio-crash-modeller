import httpx
import pytest

from crashmodel import __version__
from crashmodel.data import diagnostics
from crashmodel.data.diagnostics import DataSource

SOURCE = DataSource("Example source", "https://data.example.com/series.csv", "Testing")


def client_returning(response: httpx.Response) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda _request: response))


def client_failing_with(error: httpx.HTTPError) -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise error

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_a_successful_response_is_reachable_with_its_size_and_timing() -> None:
    with client_returning(httpx.Response(200, content=b"x" * 2048)) as client:
        result = diagnostics.check_source(client, SOURCE)

    assert result.reachable
    assert result.status_code == 200
    assert result.size_bytes == 2048
    assert result.elapsed_ms is not None
    assert result.elapsed_ms >= 0
    assert result.error is None


def test_an_error_status_is_unreachable_with_its_reason() -> None:
    with client_returning(httpx.Response(503)) as client:
        result = diagnostics.check_source(client, SOURCE)

    assert not result.reachable
    assert result.status_code == 503
    assert result.error == "Service Unavailable"


def test_a_transport_failure_is_unreachable_without_raising() -> None:
    with client_failing_with(httpx.ConnectError("no route")) as client:
        result = diagnostics.check_source(client, SOURCE)

    assert not result.reachable
    assert result.status_code is None
    assert result.error == "ConnectError"


def test_check_sources_checks_each_source_in_order() -> None:
    other = DataSource("Other source", "https://other.example.com/", "Testing")
    with client_returning(httpx.Response(200)) as client:
        results = diagnostics.check_sources(client, [SOURCE, other])

    assert [result.source for result in results] == [SOURCE, other]


def test_the_client_identifies_the_project_without_personal_details() -> None:
    with diagnostics.make_client() as client:
        agent = client.headers["User-Agent"]

    assert agent.startswith(f"crashmodel/{__version__}")
    assert "@" not in agent


@pytest.mark.parametrize("source", diagnostics.HOSTED_SOURCES)
def test_hosted_sources_use_https(source: DataSource) -> None:
    assert source.url.startswith("https://")
