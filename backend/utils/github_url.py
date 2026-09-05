"""Parsing of GitHub Pull Request URLs"""
from __future__ import annotations

import re

from models.pr import PullRequestReference

_PR_URL_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[^/\s]+)/(?P<repository>[^/\s]+)/pull/(?P<number>\d+)/?$"
)


class InvalidPullRequestUrlError(ValueError):
    """Raised when a string is not a valid GitHub Pull Request URL"""


def parse_pull_request_url(url: str) -> PullRequestReference:
    """Parse a GitHub PR URL into a strongly typed reference

    Example input: https://github.com/owner/repository/pull/123
    """
    match = _PR_URL_PATTERN.match(url.strip())
    if not match:
        raise InvalidPullRequestUrlError(
            f"'{url}' is not a valid GitHub pull request URL. "
            "Expected format: https://github.com/<owner>/<repository>/pull/<number>"
        )

    owner = match.group("owner")
    repository = match.group("repository")
    number = int(match.group("number"))

    return PullRequestReference(
        owner=owner,
        repository=repository,
        number=number,
        url=url,
    )
