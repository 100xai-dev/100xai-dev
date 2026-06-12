import Link from "next/link";
import { notFound } from "next/navigation";

import { JobStatusBadge } from "@/components/brand/job-status-badge";
import { getBrand, getPipelineStatus } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoBrand, demoBrandJobs } from "@/lib/demo-data";

type PageProps = { params: { id: string } };

type PipelineRun = {
  id: string;
  status: string;
  stage: string | null;
  job_type: string;
  created_at: string | null;
  auto_triggered: boolean;
};

const TYPE_LABEL: Record<string, string> = {
  keyword_research: "Pipeline 1 · Keyword Research",
  serp_analysis: "Pipeline 2 · SERP Analysis",
  content_generation: "Pipeline 3 · Content Generation",
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function BrandJobsPage({ params }: PageProps) {
  const demo = isDemoMode();

  let brand;
  let runs: PipelineRun[] = [];
  let loadError = "";

  if (demo) {
    brand = demoBrand(params.id);
    runs = demoBrandJobs(params.id).map((j) => ({
      id: j.id,
      status: j.status,
      stage: j.stage,
      job_type: j.job_type,
      created_at: j.started_at,
      auto_triggered: false,
    }));
  } else {
    try {
      brand = await getBrand(params.id);
    } catch {
      notFound();
    }
    try {
      const data = await getPipelineStatus(params.id);
      const groups = data.pipeline_status;
      const all = [
        ...groups.pipeline_1_keyword_research.map((j) => ({ ...j, job_type: "keyword_research" })),
        ...groups.pipeline_2_serp_analysis.map((j) => ({ ...j, job_type: "serp_analysis" })),
        ...groups.pipeline_3_content_generation.map((j) => ({ ...j, job_type: "content_generation" })),
      ];
      runs = all
        .map((j) => ({
          id: j.id,
          status: j.status,
          stage: j.stage,
          job_type: j.job_type,
          created_at: j.created_at,
          auto_triggered: j.auto_triggered,
        }))
        .sort((a, b) => {
          const at = a.created_at ? new Date(a.created_at).getTime() : 0;
          const bt = b.created_at ? new Date(b.created_at).getTime() : 0;
          return bt - at;
        });
    } catch (err) {
      loadError = err instanceof Error ? err.message : "Failed to load pipeline runs";
    }
  }

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}`}>{brand.name}</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Pipelines</span>
      </nav>

      <div className="page-head">
        <div>
          <h1 className="page-title">Pipeline Runs</h1>
          <p className="page-subtitle">Keyword research → SERP analysis → content generation for this brand.</p>
        </div>
        <Link className="topbar-link primary" href={`/brands/${brand.id}/jobs/new`} style={{ height: 40, padding: "0 18px" }}>
          + Run Keyword Pipeline
        </Link>
      </div>

      {loadError && <div className="alert alert-danger">{loadError}</div>}

      {!loadError && runs.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: "56px 24px" }}>
          <div style={{ fontSize: "2rem", marginBottom: "12px" }}>✦</div>
          <p style={{ fontWeight: 500, color: "var(--text)" }}>No pipeline runs yet.</p>
          <p className="meta" style={{ marginTop: 4 }}>Seed a keyword to start the first run.</p>
        </div>
      )}

      {!loadError && runs.length > 0 && (
        <div className="stack stack-sm">
          {runs.map((run) => (
            <div
              key={run.id}
              className="card-flat"
              style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 18px", flexWrap: "wrap" }}
            >
              <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text)", minWidth: 230 }}>
                {TYPE_LABEL[run.job_type] ?? run.job_type}
              </span>
              <JobStatusBadge status={run.status} />
              <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{run.stage ?? "—"}</span>
              {run.auto_triggered && (
                <span className="status-badge" style={{ color: "var(--info)", background: "var(--info-light)", borderColor: "var(--info-border)" }}>
                  auto
                </span>
              )}
              <span className="meta" style={{ marginLeft: "auto" }}>{formatDate(run.created_at)}</span>
              <Link className="pill-link" href={`/brands/${brand.id}/jobs/${run.id}`} style={{ fontSize: "0.8125rem", height: 34 }}>
                View →
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
