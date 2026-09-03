import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function App() {
  const [prUrl, setPrUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [review, setReview] = useState(null);
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
      const response = await fetch("http://localhost:8000/api/review", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pr_url: prUrl.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to review pull request.");
      }

      setReview(data.review);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-12">
        <header className="mb-12">
          <p className="mb-3 text-sm font-medium text-muted-foreground">
            AI CODE REVIEW
          </p>

          <h1 className="text-4xl font-bold tracking-tight">
            Pull Request Reviewer
          </h1>

          <p className="mt-3 max-w-2xl text-muted-foreground">
            Analyze GitHub pull requests using specialized AI agents for
            quality, security, bugs, and performance.
          </p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>Review a pull request</CardTitle>
          </CardHeader>

          <CardContent>
            <div className="flex gap-3">
              <Input
                value={prUrl}
                onChange={(event) => setPrUrl(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    handleReview();
                  }
                }}
                placeholder="https://github.com/owner/repository/pull/42"
                disabled={loading}
              />

              <Button onClick={handleReview} disabled={loading}>
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

        {review && (
          <div className="mt-8">
            <Card>
              <CardHeader>
                <CardTitle>Review Result</CardTitle>
              </CardHeader>

              <CardContent>
                <pre className="overflow-auto text-sm">
                  {JSON.stringify(review, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </main>
  );
}

export default App;