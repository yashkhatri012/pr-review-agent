import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface ReviewInputProps {
  prUrl: string;
  setPrUrl: (value: string) => void;
  isReviewing: boolean;
  isAuthenticated: boolean;
  onSubmit: () => void;
}

export function ReviewInput({
  prUrl,
  setPrUrl,
  isReviewing,
  isAuthenticated,
  onSubmit,
}: ReviewInputProps) {
  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <div>
          <h2 className="font-semibold">Review a Pull Request</h2>

          <p className="mt-1 text-sm text-muted-foreground">
            You get{" "}
            <span className="font-medium text-foreground">
              one free PR review per account
            </span>
            . Sign in with Google to use it.
          </p>
        </div>

        <div className="flex gap-3">
          <Input
            value={prUrl}
            onChange={(event) => setPrUrl(event.target.value)}
            placeholder="https://github.com/owner/repository/pull/42"
            disabled={isReviewing}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !isReviewing) {
                onSubmit();
              }
            }}
          />

          <Button
            onClick={onSubmit}
            disabled={isReviewing || !prUrl.trim()}
          >
            {isReviewing
              ? "Reviewing..."
              : isAuthenticated
                ? "Review PR"
                : "Sign in to Get 1 Free Review"}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">
          After your free review, you can deploy your own instance and use
          your own API keys.
        </p>
      </CardContent>
    </Card>
  );
}