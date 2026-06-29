import { LibraryView } from "@/components/library/library-view";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Caption Library</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Source videos under <code>source/</code> grouped with the caption
          sets derived from them under <code>captions/</code>. For the full
          bucket, see Files.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <LibraryView />
      </div>
    </div>
  );
}
