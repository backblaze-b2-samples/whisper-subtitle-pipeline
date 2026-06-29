import { test, expect } from "@playwright/test";

// Verifies the regression where the job detail player showed the SOURCE-language
// caption track while labeling it the target language. The player must render a
// track per VTT and default to the translated (target) track, with cues that
// actually differ from the source. Skips cleanly when the environment has no
// suitable translate job (e.g. fresh CI with no B2 data).

const API = process.env.API_BASE ?? "http://localhost:8000";

test.describe("Translated captions", () => {
  test("player defaults to the translated (target) track", async ({ page, request }) => {
    test.setTimeout(60_000);

    const res = await request.get(`${API}/jobs`);
    expect(res.ok()).toBeTruthy();
    const jobs = await res.json();

    const hasVtt = (j: { artifacts?: { kind: string; language: string }[] }, lang: string) =>
      (j.artifacts ?? []).some((a) => a.kind === "vtt" && a.language === lang);

    type JobRow = Record<string, unknown> & {
      id: string; task: string; status: string;
      target_language: string; detected_language: string | null;
      languages?: string[]; artifacts?: { kind: string; language: string }[];
    };
    const isValid = (j: JobRow) =>
      j.task === "translate" &&
      j.status === "succeeded" &&
      !!j.detected_language &&
      j.target_language !== j.detected_language &&
      hasVtt(j, j.target_language) &&
      hasVtt(j, j.detected_language as string);

    // Optionally pin a specific job (the exact scenario under test); otherwise
    // pick any valid translate job.
    const pinned = process.env.JOB_ID;
    const job = pinned
      ? (jobs as JobRow[]).find((j) => j.id === pinned && isValid(j))
      : (jobs as JobRow[]).find(isValid);

    test.skip(!job, "No succeeded translate job with a distinct target language available");
    const sourceLang = job!.detected_language as string;
    const targetLang = job!.target_language;

    await page.goto(`/jobs/${job!.id}`);
    await expect(page.locator("video")).toBeVisible();

    // One <track> per VTT language: source + target.
    await page.waitForFunction(
      (n) => (document.querySelector("video")?.textTracks.length ?? 0) >= n,
      2,
      { timeout: 30_000 },
    );

    // The default visible track must be the TARGET language (the bug showed source).
    const showingLang = await page
      .waitForFunction(
        () => {
          const tt = document.querySelector("video")!.textTracks;
          for (let i = 0; i < tt.length; i++) if (tt[i].mode === "showing") return tt[i].language;
          return null;
        },
        undefined,
        { timeout: 30_000 },
      )
      .then((h) => h.jsonValue());
    expect(showingLang, "default visible caption track is the target language").toBe(targetLang);

    // Load every track's cues and confirm the target text is real and differs
    // from the source (i.e. translation actually happened, not a relabel).
    const cueByLang = await page.evaluate(async () => {
      const tt = document.querySelector("video")!.textTracks;
      for (let i = 0; i < tt.length; i++) tt[i].mode = "hidden";
      const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
      const out: Record<string, string> = {};
      for (let attempt = 0; attempt < 60; attempt++) {
        let ready = true;
        for (let i = 0; i < tt.length; i++) {
          const cues = tt[i].cues;
          if (cues && cues.length > 0) out[tt[i].language] = (cues[0] as VTTCue).text;
          else ready = false;
        }
        if (ready) break;
        await sleep(250);
      }
      return out;
    });

    expect(cueByLang[sourceLang], "source track has cues").toBeTruthy();
    expect(cueByLang[targetLang], "target track has cues").toBeTruthy();
    expect(
      cueByLang[targetLang],
      "translated caption text must differ from the source",
    ).not.toBe(cueByLang[sourceLang]);

    test.info().annotations.push({
      type: "captions",
      description: `source(${sourceLang})=${cueByLang[sourceLang]} | target(${targetLang})=${cueByLang[targetLang]}`,
    });
  });
});
