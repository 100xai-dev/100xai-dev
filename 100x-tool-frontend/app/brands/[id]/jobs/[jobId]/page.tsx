import { notFound } from "next/navigation";

import { JobOutputTabs } from "@/components/brand/job-output-tabs";
import { JobStatusLive } from "@/components/brand/job-status-live";
import { getJob, listKeywords, getSerpAnalysis, getBlogJob } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoDraft, demoJob, demoKeywords, demoSerp } from "@/lib/demo-data";
import type { BlogDraftOut, KeywordOut, SerpAnalysisItem } from "@/lib/types";

type PageProps = {
  params: { id: string; jobId: string };
};

export default async function BrandJobPage({ params }: PageProps) {
  const demo = isDemoMode();
  const brandId = params.id;
  const jobId = params.jobId;

  let job;
  if (demo) {
    job = demoJob(brandId, jobId);
  } else {
    try {
      job = await getJob(jobId);
    } catch {
      notFound();
    }
  }

  let keywords: KeywordOut[] = [];
  let serp: SerpAnalysisItem[] = [];
  let draft: BlogDraftOut | null = null;

  if (demo) {
    keywords = demoKeywords(brandId, jobId);
    serp = demoSerp(brandId, jobId);
    draft = job.stage === "COMPLETE" ? demoDraft(jobId) : null;
  } else {
    // Pipeline outputs are brand-scoped on the backend. Fetch all three in
    // parallel; one failure must not break the others. The draft (if any) lives
    // on the BlogJob that shares this job's id (content_generation jobs).
    const [keywordsResult, serpResult, blogResult] = await Promise.allSettled([
      listKeywords(brandId),
      getSerpAnalysis(brandId),
      getBlogJob(brandId, jobId),
    ]);

    keywords = keywordsResult.status === "fulfilled" ? keywordsResult.value.keywords : [];
    serp = serpResult.status === "fulfilled" ? serpResult.value.serp_analyses : [];
    draft = blogResult.status === "fulfilled" ? blogResult.value.draft : null;
  }

  const showKeywords = keywords.length > 0;
  const showSerp = serp.length > 0;
  const showDraft = draft !== null;

  return (
    <div className="stack stack-lg">
      <JobStatusLive jobId={jobId} initial={job} variant="full" />

      <JobOutputTabs
        jobId={jobId}
        brandId={brandId}
        initialKeywords={keywords}
        initialSerp={serp}
        initialDraft={draft}
        showKeywords={showKeywords}
        showSerp={showSerp}
        showDraft={showDraft}
      />
    </div>
  );
}
