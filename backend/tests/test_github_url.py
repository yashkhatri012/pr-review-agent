import pytest

from utils.github_url import InvalidPullRequestUrlError, parse_pull_request_url


def test_parses_valid_pr_url():
    ref = parse_pull_request_url("https://github.com/owner/repository/pull/123")
    assert ref.owner == "owner"
    assert ref.repository == "repository"
    assert ref.number == 123
    assert ref.url == "https://github.com/owner/repository/pull/123"


def test_parses_pr_url_with_trailing_slash():
    ref = parse_pull_request_url("https://github.com/owner/repository/pull/123/")
    assert ref.number == 123


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/owner/repository",
        "https://github.com/owner/repository/pull/abc",
        "https://gitlab.com/owner/repository/pull/123",
        "not a url",
        "",
    ],
)
def test_rejects_invalid_urls(url):
    with pytest.raises(InvalidPullRequestUrlError):
        parse_pull_request_url(url)
