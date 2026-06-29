"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Play, Pencil, Trash2, Download, FileText } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { GeneratingLoader } from "@/components/ui/generating-loader";
import {
  useDeleteJob,
  useJob,
  useRunJob,
  useUpdateJob,
} from "@/lib/queries";
import { getArtifactUrl, getSourceUrl } from "@/lib/api-client";
import type { CaptionArtifact } from "@whisper-subtitle-pipeline/shared";
import { JobForm } from "./job-form";
import { JobStatusBadge } from "./job-status-badge";

function ArtifactRow({ jobId, artifact }: { jobId: string; artifact: CaptionArtifact }) {
  const download = async () => {
    try {
      const { url } = await getArtifactUrl(jobId, artifact.key);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      toast.error("Could not generate download link");
    }
  };
  return (
    <div className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <FileText className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono text-xs uppercase">{artifact.kind}</span>
        <span className="text-muted-foreground">· {artifact.language}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-foreground tabular-nums">
          {artifact.size_human}
        </span>
        <Button variant="ghost" size="sm" className="h-7" onClick={download}>
          <Download className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

export function JobDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: job, isLoading, error, refetch } = useJob(id);
  const runJob = useRunJob();
  const updateJob = useUpdateJob(id);
  const deleteJob = useDeleteJob();
  const [editOpen, setEditOpen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [trackUrls, setTrackUrls] = useState<Record<string, string>>({});

  // Fetch a presigned source-video URL plus a presigned URL for EVERY VTT
  // caption track, so the player can offer each language. A translate job has
  // two (source + target); we default to the translated one below.
  const sourceKey = job?.source_key;
  const vttArtifacts = useMemo(
    () => job?.artifacts.filter((a) => a.kind === "vtt") ?? [],
    [job?.artifacts],
  );
  // The track shown by default: the translated (target) language when it
  // exists, otherwise the only (source) track.
  const defaultVttLang =
    vttArtifacts.find((a) => a.language === job?.target_language)?.language ??
    vttArtifacts[0]?.language;

  useEffect(() => {
    let active = true;
    if (sourceKey && job?.status === "succeeded") {
      getSourceUrl(sourceKey)
        .then((r) => active && setVideoUrl(r.url))
        .catch(() => active && setVideoUrl(null));
    }
    if (vttArtifacts.length > 0) {
      Promise.all(
        vttArtifacts.map((a) =>
          getArtifactUrl(id, a.key)
            .then((r) => [a.key, r.url] as const)
            .catch(() => null),
        ),
      ).then((pairs) => {
        if (!active) return;
        setTrackUrls(
          Object.fromEntries(
            pairs.filter((p): p is readonly [string, string] => p !== null),
          ),
        );
      });
    }
    return () => {
      active = false;
    };
  }, [id, sourceKey, job?.status, vttArtifacts]);

  // Force the default-language track to actually display. A <track> added to
  // the DOM after the <video> mounts (our URLs resolve async) is not reliably
  // shown by the browser, so we set the track modes explicitly once they exist.
  useEffect(() => {
    const v = videoRef.current;
    if (!v || !defaultVttLang) return;
    const apply = () => {
      for (let i = 0; i < v.textTracks.length; i++) {
        const t = v.textTracks[i];
        t.mode = t.language === defaultVttLang ? "showing" : "disabled";
      }
    };
    apply();
    v.textTracks.addEventListener("addtrack", apply);
    return () => v.textTracks.removeEventListener("addtrack", apply);
  }, [defaultVttLang, trackUrls]);

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }
  if (error || !job) {
    return <ErrorState error={error ?? new Error("Job not found")} onRetry={() => refetch()} />;
  }

  const isWorking = job.status === "pending" || job.status === "running";

  return (
    <div className="space-y-6">
      {/* Header / actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title">{job.source_filename}</h1>
            <JobStatusBadge status={job.status} />
          </div>
          <p className="text-sm text-muted-foreground mt-1.5 capitalize">
            {job.task} · model {job.model_size} ·{" "}
            {job.detected_language ?? job.source_language} → {job.target_language}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={runJob.isPending || isWorking}
            onClick={() =>
              runJob.mutate(job.id, {
                onSuccess: () => toast.success("Job re-running"),
                onError: () => toast.error("Could not start the job"),
              })
            }
          >
            <Play className="h-3.5 w-3.5" />
            {job.status === "succeeded" || job.status === "failed"
              ? "Re-run"
              : "Run"}
          </Button>
          <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>
            <Pencil className="h-3.5 w-3.5" />
            Edit
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="outline">
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this job?</AlertDialogTitle>
                <AlertDialogDescription>
                  This removes the job and its caption files under{" "}
                  <code>captions/{job.id}/</code> in B2. The source video is
                  not deleted. This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() =>
                    deleteJob.mutate(job.id, {
                      onSuccess: () => {
                        toast.success("Job deleted");
                        router.push("/jobs");
                      },
                      onError: () => toast.error("Delete failed"),
                    })
                  }
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Running state */}
      {isWorking && (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-10">
            <GeneratingLoader size="lg" label="Transcribing…" />
            <p className="text-sm text-muted-foreground">
              faster-whisper is processing this video on-device. This page
              updates automatically.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Failed state */}
      {job.status === "failed" && (
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-destructive">
              {job.error ?? "Transcription failed."}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Use Re-run to try again.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Succeeded: player + transcript + downloads */}
      {job.status === "succeeded" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader className="border-b border-border py-4 px-5">
              <CardTitle className="card-title">Player</CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              {videoUrl ? (
                <video
                  key={videoUrl}
                  ref={videoRef}
                  controls
                  className="w-full rounded-md bg-black"
                  crossOrigin="anonymous"
                >
                  <source src={videoUrl} />
                  {vttArtifacts.map((a) =>
                    trackUrls[a.key] ? (
                      <track
                        key={a.key}
                        default={a.language === defaultVttLang}
                        kind="subtitles"
                        srcLang={a.language}
                        label={`Captions (${a.language})`}
                        src={trackUrls[a.key]}
                      />
                    ) : null,
                  )}
                </video>
              ) : (
                <Skeleton className="h-56 w-full" />
              )}
              <p className="text-xs text-muted-foreground mt-2">
                Captions are served from a WebVTT track stored in B2.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-border py-4 px-5">
              <CardTitle className="card-title">
                Caption artifacts ({job.artifacts.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5 space-y-2">
              {job.artifacts.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No artifacts yet.
                </p>
              ) : (
                job.artifacts.map((a) => (
                  <ArtifactRow key={a.key} jobId={job.id} artifact={a} />
                ))
              )}
              <p className="text-xs text-muted-foreground pt-2">
                Languages: {job.languages.join(", ") || "—"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Edit dialog — opens pre-filled with the job's real values */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Job</DialogTitle>
          </DialogHeader>
          <JobForm
            mode="edit"
            job={job}
            submitting={updateJob.isPending}
            onSubmit={async (values) => {
              await updateJob.mutateAsync(values);
              setEditOpen(false);
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
