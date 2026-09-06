from prometheus_client import Counter, Histogram


review_requests_total = Counter(
    "review_requests_total",
    "Total number of pull request reviews started.",
)


review_duration_seconds = Histogram(
    "review_duration_seconds",
    "Time taken to complete a pull request review.",
)

agent_duration_seconds = Histogram(
    "agent_duration_seconds",
    "Time taken by a review agent to complete.",
    labelnames=["agent"],
    buckets=[1, 2.5, 5, 10, 15, 30, 60, 120],
)