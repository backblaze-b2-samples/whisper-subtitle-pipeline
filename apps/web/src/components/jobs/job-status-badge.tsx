"use client";

import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@whisper-subtitle-pipeline/shared";

const LABELS: Record<JobStatus, string> = {
  pending: "Pending",
  running: "Transcribing",
  succeeded: "Succeeded",
  failed: "Failed",
};

const VARIANTS: Record<
  JobStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  pending: "secondary",
  running: "secondary",
  succeeded: "default",
  failed: "destructive",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return <Badge variant={VARIANTS[status]}>{LABELS[status]}</Badge>;
}
