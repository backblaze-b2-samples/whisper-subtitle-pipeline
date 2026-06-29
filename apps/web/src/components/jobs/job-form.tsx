"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useFiles, useJobOptions } from "@/lib/queries";
import type { Job, JobCreate, ModelSize } from "@whisper-subtitle-pipeline/shared";

const jobSchema = z.object({
  source_key: z.string().min(1, "Select a source video"),
  source_language: z.string().min(1),
  target_language: z.string().min(1),
  model_size: z.enum(["tiny", "base", "small", "medium", "large-v3"]),
  task: z.enum(["transcribe", "translate"]),
});

type JobValues = z.infer<typeof jobSchema>;

// Create-form safe defaults — surfaced as FormDescription hints (never an
// autofill button). The edit form overrides these with the job's real values.
const CREATE_DEFAULTS: JobValues = {
  source_key: "",
  source_language: "auto",
  target_language: "en",
  model_size: "base",
  task: "translate",
};

interface JobFormProps {
  mode: "create" | "edit";
  job?: Job;
  onSubmit: (values: JobCreate) => Promise<unknown>;
  submitting?: boolean;
}

export function JobForm({ mode, job, onSubmit, submitting }: JobFormProps) {
  const router = useRouter();
  const { data: options } = useJobOptions();
  // Source videos live under the source/ prefix in B2.
  const { data: sources = [] } = useFiles("source/", 200);

  const defaults: JobValues = job
    ? {
        source_key: job.source_key,
        source_language: job.source_language,
        target_language: job.target_language,
        model_size: job.model_size,
        task: job.task,
      }
    : CREATE_DEFAULTS;

  const form = useForm<JobValues>({
    resolver: zodResolver(jobSchema),
    defaultValues: defaults,
  });

  const languages = options?.languages ?? [{ code: "auto", label: "Auto-detect" }];
  const models: ModelSize[] =
    options?.models ?? ["tiny", "base", "small", "medium", "large-v3"];
  // Target language excludes "auto" — you can't translate to "detect".
  const targetLanguages = languages.filter((l) => l.code !== "auto");

  const handleSubmit = async (values: JobValues) => {
    try {
      await onSubmit(values);
      toast.success(mode === "create" ? "Job created" : "Job updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong");
    }
  };

  const isCreate = mode === "create";

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">
              {isCreate ? "New Subtitle Job" : "Edit Job"}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-6">
            <FormField
              control={form.control}
              name="source_key"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Source video</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full md:w-[28rem]">
                        <SelectValue placeholder="Choose a video from source/" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {sources.length === 0 ? (
                        <SelectItem value="__none" disabled>
                          No videos yet — upload one first
                        </SelectItem>
                      ) : (
                        sources.map((f) => (
                          <SelectItem key={f.key} value={f.key}>
                            {f.filename}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Pick a video uploaded to the <code>source/</code> prefix.
                    Add more on the Upload page.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-6 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="source_language"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Source language</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {languages.map((l) => (
                          <SelectItem key={l.code} value={l.code}>
                            {l.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {isCreate && (
                      <FormDescription>
                        Default <strong>Auto-detect</strong> lets Whisper
                        identify the spoken language.
                      </FormDescription>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="target_language"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Translate to</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {targetLanguages.map((l) => (
                          <SelectItem key={l.code} value={l.code}>
                            {l.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {isCreate && (
                      <FormDescription>
                        Default <strong>English</strong>. Used only when the
                        task includes translation.
                      </FormDescription>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="model_size"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model size</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-60">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {models.map((m) => (
                        <SelectItem key={m} value={m}>
                          {m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {isCreate && (
                    <FormDescription>
                      Default <strong>base</strong> (fast). Use{" "}
                      <strong>large-v3</strong> for best quality (slower, ~3 GB
                      download on first use).
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="task"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Task</FormLabel>
                  <FormControl>
                    <RadioGroup
                      onValueChange={field.onChange}
                      value={field.value}
                      className="flex flex-col gap-2 sm:flex-row sm:gap-6"
                    >
                      <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <RadioGroupItem value="transcribe" />
                        Transcribe only
                      </label>
                      <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <RadioGroupItem value="translate" />
                        Transcribe + Translate
                      </label>
                    </RadioGroup>
                  </FormControl>
                  {isCreate && (
                    <FormDescription>
                      Default <strong>Transcribe + Translate</strong> emits the
                      source captions and a translated set.
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting
              ? "Saving..."
              : isCreate
                ? "Create & run"
                : "Save changes"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
