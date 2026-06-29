export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Subtitle pipeline ---

export type JobStatus = "pending" | "running" | "succeeded" | "failed";
export type JobTask = "transcribe" | "translate";
export type ModelSize = "tiny" | "base" | "small" | "medium" | "large-v3";

export interface CaptionArtifact {
  kind: "srt" | "vtt" | "json";
  language: string;
  key: string;
  size_bytes: number;
  size_human: string;
}

export interface Job {
  id: string;
  source_key: string;
  source_filename: string;
  source_language: string;
  target_language: string;
  model_size: ModelSize;
  task: JobTask;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  detected_language: string | null;
  languages: string[];
  artifacts: CaptionArtifact[];
  duration_seconds: number | null;
  error: string | null;
  progress: number;
}

export interface JobCreate {
  source_key: string;
  source_language: string;
  target_language: string;
  model_size: ModelSize;
  task: JobTask;
}

export interface JobOptions {
  languages: { code: string; label: string }[];
  models: ModelSize[];
  tasks: string[];
  default_model: ModelSize;
}

export interface LibraryEntry {
  source_key: string;
  source_filename: string;
  source_size_bytes: number;
  source_size_human: string;
  job_id: string | null;
  status: string | null;
  languages: string[];
  artifacts: CaptionArtifact[];
  captions_size_bytes: number;
  captions_size_human: string;
}

export interface PipelineStats {
  videos_processed: number;
  caption_files: number;
  languages_covered: number;
  source_size_bytes: number;
  source_size_human: string;
  captions_size_bytes: number;
  captions_size_human: string;
  derived_ratio: number;
  total_b2_size_bytes: number;
  total_b2_size_human: string;
}
