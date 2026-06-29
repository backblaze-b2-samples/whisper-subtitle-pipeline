import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Upload Source Videos</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Drag videos in or click to browse. They land under the{" "}
          <code>source/</code> prefix in B2, ready to subtitle from the Jobs
          page. MP4, MOV, MKV, WebM, and AVI are supported.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
