"use client";

import { use } from "react";
import { JobDetail } from "@/components/jobs/job-detail";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return (
    <div className="space-y-8">
      <div className="animate-fade-in-up">
        <JobDetail id={id} />
      </div>
    </div>
  );
}
