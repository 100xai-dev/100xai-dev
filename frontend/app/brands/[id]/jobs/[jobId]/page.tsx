import { notFound } from "next/navigation";

import { JobStatusLive } from "@/components/brand/job-status-live";
import { getJob } from "@/lib/api";

type PageProps = {
  params: { id: string; jobId: string };
};

export default async function BrandJobPage({ params }: PageProps) {
  let job;
  try {
    job = await getJob(params.jobId);
  } catch {
    notFound();
  }

  return <JobStatusLive jobId={params.jobId} initial={job} variant="full" />;
}
