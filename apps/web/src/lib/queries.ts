"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  createJob,
  deleteFile,
  deleteJob,
  getFiles,
  getFileStats,
  getJob,
  getJobOptions,
  getJobs,
  getLibrary,
  getPipelineStats,
  getPreviewUrl,
  getUploadActivity,
  runJob,
  updateJob,
} from "@/lib/api-client";
import type {
  FileMetadata,
  Job,
  JobCreate,
} from "@whisper-subtitle-pipeline/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  jobs: () => [...qk.all, "jobs"] as const,
  job: (id: string) => [...qk.all, "jobs", id] as const,
  jobOptions: () => [...qk.all, "jobs", "options"] as const,
  library: () => [...qk.all, "library"] as const,
  pipelineStats: () => [...qk.all, "library", "stats"] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Subtitle jobs ---

export function useJobOptions() {
  return useQuery({
    queryKey: qk.jobOptions(),
    queryFn: getJobOptions,
    staleTime: 5 * 60_000,
  });
}

export function useJobs() {
  return useQuery<Job[], ApiError>({
    queryKey: qk.jobs(),
    queryFn: getJobs,
    // Poll the list while any job is still working so cards update live.
    refetchInterval: (query) => {
      const data = query.state.data;
      const active = data?.some(
        (j) => j.status === "pending" || j.status === "running",
      );
      return active ? 2500 : false;
    },
  });
}

export function useJob(id: string | undefined) {
  return useQuery<Job, ApiError>({
    queryKey: qk.job(id ?? ""),
    queryFn: () => getJob(id as string),
    enabled: !!id,
    // Poll the detail view while the job is still working.
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "pending" || s === "running" ? 2000 : false;
    },
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: JobCreate) => createJob(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useUpdateJob(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: JobCreate) => updateJob(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useRunJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => runJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

// --- Caption library ---

export function useLibrary() {
  return useQuery({
    queryKey: qk.library(),
    queryFn: getLibrary,
  });
}

export function usePipelineStats() {
  return useQuery({
    queryKey: qk.pipelineStats(),
    queryFn: getPipelineStats,
  });
}
