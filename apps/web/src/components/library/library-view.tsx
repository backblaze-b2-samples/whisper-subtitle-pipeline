"use client";

import Link from "next/link";
import { Film, ArrowRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useLibrary } from "@/lib/queries";

export function LibraryView() {
  const { data: entries = [], isLoading, error, refetch } = useLibrary();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-40 w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={Film}
        title="No source videos yet"
        description="Upload a video, then create a subtitle job to populate the library."
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {entries.map((entry) => (
        <Card key={entry.source_key} className="card-hover">
          <CardHeader className="border-b border-border py-4 px-5 flex flex-row items-center justify-between">
            <CardTitle className="card-title truncate">
              {entry.source_filename}
            </CardTitle>
            {entry.status && (
              <Badge variant={entry.status === "succeeded" ? "default" : "secondary"}>
                {entry.status}
              </Badge>
            )}
          </CardHeader>
          <CardContent className="p-5 space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Source size</span>
              <span className="tabular-nums">{entry.source_size_human}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Captions size</span>
              <span className="tabular-nums">{entry.captions_size_human}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Caption files</span>
              <span className="tabular-nums">{entry.artifacts.length}</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {entry.languages.length > 0 ? (
                entry.languages.map((lang) => (
                  <Badge key={lang} variant="outline">
                    {lang}
                  </Badge>
                ))
              ) : (
                <span className="text-xs text-muted-foreground">
                  No captions yet
                </span>
              )}
            </div>
            {entry.job_id && (
              <Link
                href={`/jobs/${entry.job_id}`}
                className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors pt-1"
              >
                Open job
                <ArrowRight className="h-3 w-3" />
              </Link>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
