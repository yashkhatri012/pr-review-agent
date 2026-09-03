import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

interface Finding {
  severity: string;
  file: string;
  line: number;
  title: string;
  review_comment: string;
  why_it_matters: string;
  suggested_fix: string;
}

interface FindingCardProps {
  finding: Finding;
}

const severityConfig = {
  critical: {
    label: "Critical",
    variant: "destructive" as const,
  },
  high: {
    label: "High",
    variant: "destructive" as const,
  },
  medium: {
    label: "Medium",
    variant: "secondary" as const,
  },
  low: {
    label: "Low",
    variant: "outline" as const,
  },
  info: {
    label: "Info",
    variant: "outline" as const,
  },
};

export function FindingCard({ finding }: FindingCardProps) {
  const config =
    severityConfig[
      finding.severity as keyof typeof severityConfig
    ] ?? {
      label: finding.severity,
      variant: "outline" as const,
    };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="text-lg">
              {finding.title}
            </CardTitle>

            <p className="mt-2 font-mono text-sm text-muted-foreground">
              {finding.file}:{finding.line}
            </p>
          </div>

          <Badge variant={config.variant} className="w-fit">
            {config.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <div>
          <h4 className="mb-2 text-sm font-semibold">
            Review
          </h4>

          <p className="text-sm leading-6 text-muted-foreground">
            {finding.review_comment}
          </p>
        </div>

        <Separator />

        <div>
          <h4 className="mb-2 text-sm font-semibold">
            Why it matters
          </h4>

          <p className="text-sm leading-6 text-muted-foreground">
            {finding.why_it_matters}
          </p>
        </div>

        <Separator />

        <div>
          <h4 className="mb-2 text-sm font-semibold">
            Suggested fix
          </h4>

          <p className="text-sm leading-6 text-muted-foreground">
            {finding.suggested_fix}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}