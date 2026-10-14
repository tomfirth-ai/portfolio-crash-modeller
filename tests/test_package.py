import crashmodel


def test_package_exposes_its_version() -> None:
    assert crashmodel.__version__ == "0.1.0"
