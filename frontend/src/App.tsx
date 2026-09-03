import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { ReviewHeader } from "@/components/review/ReviewHeader";
import { ReviewStats } from "@/components/review/ReviewStats";
import { KeyPoints } from "@/components/review/KeyPoints";
import { FindingsList } from "@/components/review/FindingsList";

function App() {
  const [prUrl, setPrUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [review, setReview] = useState<any>(null);
  const [error, setError] = useState("");

  const handleReview = async () => {
    if (!prUrl.trim()) {
      setError("Enter a GitHub pull request URL.");
      return;
    }

    setLoading(true);
    setError("");
    setReview(null);

    try {
      const response = await fetch(
        "http://localhost:8000/api/review",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            pr_url: prUrl.trim(),
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to review pull request.",
        );
      }

      setReview(data.review);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-6 py-12">

        {/* Header */}
        <header className="mb-10">
          <p className="text-sm font-medium text-muted-foreground">
            AI CODE REVIEW
          </p>

          <h1 className="mt-2 text-4xl font-bold tracking-tight">
            Pull Request Reviewer
          </h1>

          <p className="mt-3 max-w-2xl text-muted-foreground">
            Analyze GitHub pull requests using specialized AI
            agents for quality, security, bugs, and performance.
          </p>
        </header>

        {/* Review form */}
        <Card>
          <CardHeader>
            <CardTitle>Review a pull request</CardTitle>
          </CardHeader>

          <CardContent>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Input
                value={prUrl}
                onChange={(event) =>
                  setPrUrl(event.target.value)
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    handleReview();
                  }
                }}
                placeholder="https://github.com/owner/repository/pull/42"
                disabled={loading}
              />

              <Button
                onClick={handleReview}
                disabled={loading}
                className="sm:w-32"
              >
                {loading ? "Reviewing..." : "Review PR"}
              </Button>
            </div>

            {error && (
              <p className="mt-3 text-sm text-destructive">
                {error}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        {review && (
          <div className="mt-8 space-y-6">

            <ReviewHeader
              decision={review.summary.decision}
              overview={review.summary.overview}
            />

            <ReviewStats
              total={review.summary.total_findings}
              findings={review.code_review}
            />

            <KeyPoints
              points={review.summary.key_points}
            />

            <FindingsList
              findings={review.code_review}
            />

          </div>
        )}
      </div>
    </main>
  );
}

export default App;