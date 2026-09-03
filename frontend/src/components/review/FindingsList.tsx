import { FindingCard } from "./FindingCard";

interface Finding {
  severity: string;
  file: string;
  line: number;
  title: string;
  review_comment: string;
  why_it_matters: string;
  suggested_fix: string;
}

interface FindingsListProps {
  findings: Finding[];
}

export function FindingsList({ findings }: FindingsListProps) {
  return (
    <section>
      <div className="mb-4">
        <h2 className="text-xl font-semibold tracking-tight">
          Findings
        </h2>

        <p className="text-sm text-muted-foreground">
          Issues identified by the AI review agents.
        </p>
      </div>

      <div className="space-y-4">
        {findings.map((finding, index) => (
          <FindingCard
            key={`${finding.file}-${finding.line}-${index}`}
            finding={finding}
          />
        ))}
      </div>
    </section>
  );
}