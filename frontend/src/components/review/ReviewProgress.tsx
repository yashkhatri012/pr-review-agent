import { Check, Circle, Loader2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type ProgressStatus = "pending" | "running" | "completed" | "error";

export type ReviewProgressState = Record<
  string,
  {
    status: ProgressStatus;
    message?: string;
  }
>;

interface ReviewProgressProps {
  progress: ReviewProgressState;
}

const stages = [
  {
    id: "fetching_pr",
    title: "Fetching Pull Request",
    description: "Retrieving pull request and repository information",
  },
  {
    id: "building_context",
    title: "Building Repository Context",
    description: "Preparing relevant code and documentation context",
  },
];

const specialists = [
  {
    id: "quality_review",
    title: "Quality Agent",
    description: "Analyzing code quality and maintainability",
  },
  {
    id: "security_review",
    title: "Security Agent",
    description: "Checking for security vulnerabilities",
  },
  {
    id: "bug_review",
    title: "Bug Agent",
    description: "Looking for correctness and potential bugs",
  },
  {
    id: "performance_review",
    title: "Performance Agent",
    description: "Analyzing performance and efficiency",
  },
];

const finalStages = [
  {
    id: "validate_review",
    title: "Validator",
    description: "Validating specialist findings",
  },
  {
    id: "write_review",
    title: "Review Writer",
    description: "Preparing the final pull request review",
  },
];

function StageIcon({ status }: { status: ProgressStatus }) {
  if (status === "completed") {
    return (
      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-green-500/15 text-green-500">
        <Check className="h-4 w-4" />
      </div>
    );
  }

  if (status === "running") {
    return (
      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Loader2 className="h-4 w-4 animate-spin" />
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-destructive/15 text-destructive">
        !
      </div>
    );
  }

  return (
    <div className="flex h-7 w-7 items-center justify-center text-muted-foreground">
      <Circle className="h-4 w-4" />
    </div>
  );
}

function ProgressStage({
  title,
  description,
  status,
  message,
}: {
  title: string;
  description: string;
  status: ProgressStatus;
  message?: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <StageIcon status={status} />

      <div className="min-w-0 flex-1 pt-0.5">
        <div
          className={cn(
            "font-medium transition-colors",
            status === "pending" && "text-muted-foreground",
            status === "running" && "text-foreground",
            status === "completed" && "text-foreground",
            status === "error" && "text-destructive",
          )}
        >
          {title}
        </div>

        <p className="mt-0.5 text-sm text-muted-foreground">
          {status === "running" && message ? message : description}
        </p>
      </div>
    </div>
  );
}

function getStatus(
  progress: ReviewProgressState,
  id: string,
): {
  status: ProgressStatus;
  message?: string;
} {
  return progress[id] ?? { status: "pending" };
}

export function ReviewProgress({ progress }: ReviewProgressProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Reviewing Pull Request</CardTitle>
      </CardHeader>

      <CardContent className="space-y-8">
        {/* Initial pipeline stages */}
        <div className="space-y-5">
          {stages.map((stage) => {
            const state = getStatus(progress, stage.id);

            return (
              <ProgressStage
                key={stage.id}
                title={stage.title}
                description={stage.description}
                status={state.status}
                message={state.message}
              />
            );
          })}
        </div>

        {/* Specialist agents */}
        <div>
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Specialist Analysis
          </h3>

          <div className="space-y-5">
            {specialists.map((stage) => {
              const state = getStatus(progress, stage.id);

              return (
                <ProgressStage
                  key={stage.id}
                  title={stage.title}
                  description={stage.description}
                  status={state.status}
                  message={state.message}
                />
              );
            })}
          </div>
        </div>

        {/* Final stages */}
        <div>
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Final Review
          </h3>

          <div className="space-y-5">
            {finalStages.map((stage) => {
              const state = getStatus(progress, stage.id);

              return (
                <ProgressStage
                  key={stage.id}
                  title={stage.title}
                  description={stage.description}
                  status={state.status}
                  message={state.message}
                />
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}