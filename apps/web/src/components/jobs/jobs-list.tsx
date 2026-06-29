"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Captions } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { GeneratingLoader } from "@/components/ui/generating-loader";
import { useCreateJob, useJobs } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import { JobForm } from "./job-form";
import { JobStatusBadge } from "./job-status-badge";

export function JobsList() {
  const router = useRouter();
  const { data: jobs = [], isLoading, error, refetch } = useJobs();
  const createJob = useCreateJob();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button size="sm" className="h-8" onClick={() => setDialogOpen(true)}>
          <Plus className="h-3.5 w-3.5" />
          New Job
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={Captions}
              title="No subtitle jobs yet"
              description="Create a job to transcribe and translate a source video."
            />
          ) : (
            <Table className="table-fixed">
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead className="w-[34%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Source video
                  </TableHead>
                  <TableHead className="w-[16%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Task
                  </TableHead>
                  <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Model
                  </TableHead>
                  <TableHead className="w-[18%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Created
                  </TableHead>
                  <TableHead className="w-[18%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Status
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow
                    key={job.id}
                    className="table-row-hover cursor-pointer"
                    onClick={() => router.push(`/jobs/${job.id}`)}
                  >
                    <TableCell className="font-medium">
                      <div className="truncate">{job.source_filename}</div>
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap capitalize">
                      {job.task}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                      {job.model_size}
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {formatDate(job.created_at)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {job.status === "running" || job.status === "pending" ? (
                          <GeneratingLoader size="sm" />
                        ) : null}
                        <JobStatusBadge status={job.status} />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>New Subtitle Job</DialogTitle>
          </DialogHeader>
          <JobForm
            mode="create"
            submitting={createJob.isPending}
            onSubmit={async (values) => {
              const job = await createJob.mutateAsync(values);
              setDialogOpen(false);
              router.push(`/jobs/${job.id}`);
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
