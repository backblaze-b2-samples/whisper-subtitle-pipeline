"use client";

import { Film, Captions, Languages, HardDrive, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { usePipelineStats } from "@/lib/queries";

export function PipelineStatsCards() {
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

  // The headline value prop: derived caption bytes per source byte.
  const ratio = stats ? `${stats.derived_ratio.toFixed(2)}×` : "0×";

  const cards = [
    { title: "Videos Processed", value: stats?.videos_processed ?? 0, icon: Film },
    { title: "Caption Files", value: stats?.caption_files ?? 0, icon: Captions },
    {
      title: "Languages Covered",
      value: stats?.languages_covered ?? 0,
      icon: Languages,
    },
    { title: "Derived / Source", value: ratio, icon: Layers },
    {
      title: "Total B2 Storage",
      value: stats?.total_b2_size_human ?? "0 B",
      icon: HardDrive,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
