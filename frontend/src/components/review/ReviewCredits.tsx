import { Card, CardContent } from "@/components/ui/card";
import type { User } from "@/lib/auth";

interface ReviewCreditsProps {
  user: User | null;
}

export function ReviewCredits({ user }: ReviewCreditsProps) {
  if (!user) {
    return (
      <Card>
        <CardContent className="px-6 py-4">
          <p className="text-sm text-muted-foreground">
            You get{" "}
            <span className="font-medium text-foreground">
              1 free PR review
            </span>
            . Sign in with Google to get started.
          </p>
        </CardContent>
      </Card>
    );
  }

  const reviewsLeft = user.free_review_used ? 0 : 1;

  if (reviewsLeft === 0) {
    return (
      <Card>
        <CardContent className="px-6 py-4">
          <p className="text-sm text-muted-foreground">
            You have{" "}
            <span className="font-medium text-foreground">
              0 free PR reviews
            </span>{" "}
            remaining.
          </p>

          <p className="mt-1 text-xs text-muted-foreground">
            You have already used your one free PR review. Please contact support to request additional reviews.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="px-6 py-4">
        <p className="text-sm text-muted-foreground">
          You have{" "}
          <span className="font-medium text-foreground">
            {reviewsLeft} free PR review{reviewsLeft !== 1 ? "s" : ""}
          </span>{" "}
          remaining.
        </p>
      </CardContent>
    </Card>
  );
}