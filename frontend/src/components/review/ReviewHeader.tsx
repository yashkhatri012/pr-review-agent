import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

interface ReviewHeaderProps {
  decision: string;
  overview: string;
}

const decisionConfig = {
  changes_requested: {
    label: "Changes Requested",
    variant: "destructive" as const,
  },
  approved: {
    label: "Approved",
    variant: "default" as const,
  },
  approved_with_suggestions: {
    label: "Approved with Suggestions",
    variant: "secondary" as const,
  },
};

export function ReviewHeader({
  decision,
  overview,
}: ReviewHeaderProps) {
  const config =
    decisionConfig[decision as keyof typeof decisionConfig] ?? {
      label: decision,
      variant: "secondary" as const,
    };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              AI CODE REVIEW
            </p>

            <h2 className="mt-1 text-2xl font-semibold tracking-tight">
              Review Summary
            </h2>
          </div>

          <Badge variant={config.variant} className="w-fit">
            {config.label}
          </Badge>
        </div>

        <p className="mt-6 leading-7 text-muted-foreground">
          {overview}
        </p>
      </CardContent>
    </Card>
  );
}