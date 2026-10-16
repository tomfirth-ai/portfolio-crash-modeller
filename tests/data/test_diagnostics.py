import httpx
import pytest

from crashmodel.data import diagnostics
from crashmodel.data.diagnostics import DataSource, Failure
from crashmodel.data.french import PORTFOLIO_FILES

SOURCE = DataSource("Example source", "https://data.example.com/series.csv")


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
    assert result.failure is None
    assert result.status_code == 200
    assert result.size_bytes == 2048
    assert result.elapsed_seconds is not None
    assert result.elapsed_seconds >= 0


@pytest.mark.parametrize("status_code", [404, 503, 599])
def test_an_error_status_is_unreachable_and_keeps_the_code(status_code: int) -> None:
    with client_returning(httpx.Response(status_code)) as client:
        result = diagnostics.check_source(client, SOURCE)

    assert not result.reachable
    assert result.failure is Failure.ERROR_STATUS
    assert result.status_code == status_code


@pytest.mark.parametrize(
    ("error", "failure"),
    [
        (httpx.ConnectTimeout("slow"), Failure.TIMEOUT),
        (httpx.ReadTimeout("slow"), Failure.TIMEOUT),
        (httpx.ConnectError("no route"), Failure.CONNECTION),
        (httpx.RemoteProtocolError("broken"), Failure.CONNECTION),
        (httpx.TooManyRedirects("loop"), Failure.OTHER),
    ],
)
def test_a_failed_request_is_unreachable_with_its_kind(
    error: httpx.HTTPError, failure: Failure
) -> None:
    with client_failing_with(error) as client:
        result = diagnostics.check_source(client, SOURCE)

    assert result.failure is failure
    assert result.status_code is None
    assert result.elapsed_seconds is None


def test_check_sources_checks_each_source_in_order() -> None:
    other = DataSource("Other source", "https://other.example.com/")
    with client_returning(httpx.Response(200)) as client:
        results = diagnostics.check_sources(client, [SOURCE, other])

    assert [result.source for result in results] == [SOURCE, other]


@pytest.mark.parametrize("source", diagnostics.HOSTED_SOURCES)
def test_hosted_sources_use_https(source: DataSource) -> None:
    assert source.url.startswith("https://")


def test_every_file_the_models_are_built_from_is_checked() -> None:
    assert [source.url for source in diagnostics.HOSTED_SOURCES] == [
        file.url for file in PORTFOLIO_FILES
    ]
