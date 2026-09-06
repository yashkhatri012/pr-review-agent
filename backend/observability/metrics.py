from prometheus_client import Counter


review_requests_total = Counter(
    "review_requests_total",
    "Total number of pull request reviews started.",
)