import { useRef, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/hooks/use-theme";

import { AuthButton } from "@/components/auth/AuthButton";
import { FindingsList } from "@/components/review/FindingsList";
import { KeyPoints } from "@/components/review/KeyPoints";
import { ReviewHeader } from "@/components/review/ReviewHeader";
import {
  ReviewProgress,
  type ReviewProgressState,
} from "@/components/review/ReviewProgress";
import { ReviewStats } from "@/components/review/ReviewStats";
import { ReviewCredits } from "@/components/review/ReviewCredits";
import { loginWithGoogle, type User } from "@/lib/auth";

interface ReviewResponse {
  summary: {
    decision: string;
    overview: string;
    key_points: {
      text: string;
    }[];
    total_findings: number;
  };
  code_review: {
    severity: string;
    file: string;
    line: number;
    title: string;
    review_comment: string;
    why_it_matters: string;
    suggested_fix: string;
  }[];
}

interface StartReviewResponse {
  review_id: string;
}

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [prUrl, setPrUrl] = useState("");
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [progress, setProgress] = useState<ReviewProgressState>({});
  const [isReviewing, setIsReviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const { theme, toggleTheme } = useTheme();

  const startReview = async () => {
    if (!prUrl.trim()) {
      setError("Please enter a pull request URL.");
      return;
    }

    if (!user) {
      loginWithGoogle();
      return;
    }

    if (user.free_review_used) {
      setError(
        "You have already used your one free PR review. Please contact support to request additional reviews.",
      );
      return;
    }

    setReview(null);
    setProgress({});
    setError(null);
    setIsReviewing(true);

    eventSourceRef.current?.close();

    try {
      const response = await fetch(`${API_URL}/api/review/start`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pr_url: prUrl.trim(),
        }),
      });

      if (!response.ok) {
        let message = "Failed to start pull request review.";

        try {
          const data = await response.json();

          if (typeof data.detail === "string") {
            message = data.detail;
          }
        } catch {
          // Use default message.
        }

        throw new Error(message);
      }

      const data: StartReviewResponse = await response.json();

      connectToProgressStream(data.review_id);
    } catch (err) {
      setIsReviewing(false);

      setError(
        err instanceof Error
          ? err.message
          : "Failed to start pull request review.",
      );
    }
  };

  const connectToProgressStream = (reviewId: string) => {
    const eventSource = new EventSource(
      `${API_URL}/api/review/${reviewId}/events`,
    );

    eventSourceRef.current = eventSource;

    eventSource.addEventListener("progress", (event) => {
      try {
        const data = JSON.parse(event.data);

        setProgress((previous) => ({
          ...previous,
          [data.stage]: {
            status: data.status,
            message: data.message,
          },
        }));
      } catch {
        setError("Received an invalid progress update.");
      }
    });

    eventSource.addEventListener("completed", (event) => {
      try {
        const data = JSON.parse(event.data);

        setReview(data.review);
        setIsReviewing(false);

        eventSource.close();
        eventSourceRef.current = null;
      } catch {
        setIsReviewing(false);
        setError("The review completed, but the response was invalid.");

        eventSource.close();
        eventSourceRef.current = null;
      }
    });

    eventSource.addEventListener("review_error", (event) => {
      try {
        const data = JSON.parse(event.data);

        setError(data.message || "The pull request review failed.");
      } catch {
        setError("The pull request review failed.");
      }

      setIsReviewing(false);
      eventSource.close();
      eventSourceRef.current = null;
    });

    eventSource.onerror = () => {
      if (eventSource.readyState === EventSource.CLOSED) {
        setIsReviewing(false);
        eventSourceRef.current = null;
        return;
      }

      setError("Lost connection to the review server.");
      setIsReviewing(false);

      eventSource.close();
      eventSourceRef.current = null;
    };
  };

  return (
    <main className="min-h-screen bg-background px-6 py-10 text-foreground">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              AI Pull Request Review
            </h1>

            <p className="mt-2 text-muted-foreground">
              Analyze a GitHub pull request using multiple specialized AI
              agents.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <AuthButton onAuthChange={setUser} />

            <Button
              variant="outline"
              size="icon"
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
            <ReviewCredits user={user} />
        <Card>
          <CardContent className="flex gap-3 p-6">
            <Input
              value={prUrl}
              onChange={(event) => setPrUrl(event.target.value)}
              placeholder="https://github.com/owner/repository/pull/42"
              disabled={isReviewing}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !isReviewing) {
                  startReview();
                }
              }}
            />

            <Button
              onClick={startReview}
              disabled={isReviewing || !prUrl.trim()}
            >
              {isReviewing
                ? "Reviewing..."
                : user
                  ? "Review PR"
                  : "Sign in to Review"}
            </Button>
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isReviewing && <ReviewProgress progress={progress} />}

        {review && !isReviewing && (
          <div className="space-y-6">
            <ReviewHeader
              decision={review.summary.decision}
              overview={review.summary.overview}
            />

            <ReviewStats
              total={review.summary.total_findings}
              findings={review.code_review}
            />

            <KeyPoints points={review.summary.key_points} />

            <FindingsList findings={review.code_review} />
          </div>
        )}
      </div>
    </main>
  );
}

export default App;