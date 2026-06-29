import { JobsList } from "@/components/jobs/jobs-list";

export default function JobsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Subtitle Jobs</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Transcribe and translate source videos with faster-whisper. Captions
          are written back to Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <JobsList />
      </div>
    </div>
  );
}
