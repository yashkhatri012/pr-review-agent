import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface KeyPoint {
  text: string;
}

interface KeyPointsProps {
  points: KeyPoint[];
}

export function KeyPoints({ points }: KeyPointsProps) {
  if (!points.length) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Key Points</CardTitle>
      </CardHeader>

      <CardContent>
        <ul className="space-y-3">
          {points.map((point, index) => (
            <li
              key={index}
              className="flex gap-3 text-sm leading-6 text-muted-foreground"
            >
              <span className="mt-2 size-1.5 shrink-0 rounded-full bg-foreground" />

              <span>{point.text}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}