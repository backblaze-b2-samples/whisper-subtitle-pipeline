"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { usePipelineStats } from "@/lib/queries";

export function StorageBreakdown() {
  const { data: stats, isLoading, error, refetch } = usePipelineStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const total = stats ? stats.source_size_bytes + stats.captions_size_bytes : 0;
  const sourcePct = total ? (stats!.source_size_bytes / total) * 100 : 0;
  const captionsPct = total ? (stats!.captions_size_bytes / total) * 100 : 0;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Storage breakdown</CardTitle>
        <CardDescription className="text-xs">
          Source media vs derived captions, both on Backblaze B2
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5 space-y-5">
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : (
          <>
            <div className="h-3 w-full overflow-hidden rounded-full bg-muted flex">
              <div
                className="h-full bg-[var(--chart-1)]"
                style={{ width: `${sourcePct}%` }}
              />
              <div
                className="h-full bg-[var(--chart-2)]"
                style={{ width: `${captionsPct}%` }}
              />
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground text-xs">Source media</div>
                <div className="font-semibold tabular-nums">
                  {stats?.source_size_human ?? "0 B"}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Derived captions</div>
                <div className="font-semibold tabular-nums">
                  {stats?.captions_size_human ?? "0 B"}
                </div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              A real subtitle library produces 3–5× the source size in derived
              caption artifacts across languages — a 10 TB library becomes
              30–50 TB. Every byte lives in one S3-compatible bucket.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
