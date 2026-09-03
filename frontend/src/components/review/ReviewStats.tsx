import { Card, CardContent } from "@/components/ui/card";

interface ReviewStatsProps {
  total: number;
  findings: {
    severity: string;
  }[];
}

export function ReviewStats({
  total,
  findings,
}: ReviewStatsProps) {
  const critical = findings.filter(
    (finding) => finding.severity === "critical",
  ).length;

  const high = findings.filter(
    (finding) => finding.severity === "high",
  ).length;

  const medium = findings.filter(
    (finding) => finding.severity === "medium",
  ).length;

  const low = findings.filter(
    (finding) => finding.severity === "low",
  ).length;

  const stats = [
    {
      label: "Total Findings",
      value: total,
    },
    {
      label: "Critical",
      value: critical,
    },
    {
      label: "High",
      value: high,
    },
    {
      label: "Medium",
      value: medium,
    },
    {
      label: "Low",
      value: low,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {stats.map((stat) => (
        <Card key={stat.label}>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              {stat.label}
            </p>

            <p className="mt-2 text-3xl font-semibold">
              {stat.value}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}