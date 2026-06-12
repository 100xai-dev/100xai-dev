import Link from "next/link";
import { notFound } from "next/navigation";

import { JobStatusBadge } from "@/components/brand/job-status-badge";
import { getBrand, getPipelineStatus } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoBrand, demoBrandJobs } from "@/lib/demo-data";

type PageProps = { params: { id: string } };

type AuditEntry = {
  id: string;
  status: string;
  stage: string | null;
  job_type: string;
  created_at: string | null;
};

const TYPE_LABEL: Record<string, string> = {
  keyword_research: "Keyword Research",
  serp_analysis: "SERP Analysis",
  content_generation: "Content Generation",
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

function dotColor(status: string): string {
  const s = status.toUpperCase();
  if (s === "FAILED") return "var(--danger)";
  if (s === "SUCCEEDED" || s === "COMPLETED") return "var(--success)";
  return "var(--accent)";
}

export default async function BrandAuditPage({ params }: PageProps) {
  const demo = isDemoMode();

  let brand;
  let entries: AuditEntry[] = [];
  let loadError = "";

  if (demo) {
    brand = demoBrand(params.id);
    entries = demoBrandJobs(params.id).map((j) => ({
      id: j.id,
      status: j.status,
      stage: j.stage,
      job_type: j.job_type,
      created_at: j.started_at,
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
      entries = [
        ...groups.pipeline_1_keyword_research.map((j) => ({ ...j, job_type: "keyword_research" })),
        ...groups.pipeline_2_serp_analysis.map((j) => ({ ...j, job_type: "serp_analysis" })),
        ...groups.pipeline_3_content_generation.map((j) => ({ ...j, job_type: "content_generation" })),
      ]
        .map((j) => ({ id: j.id, status: j.status, stage: j.stage, job_type: j.job_type, created_at: j.created_at }))
        .sort((a, b) => {
          const at = a.created_at ? new Date(a.created_at).getTime() : 0;
          const bt = b.created_at ? new Date(b.created_at).getTime() : 0;
          return bt - at;
        });
    } catch (err) {
      loadError = err instanceof Error ? err.message : "Failed to load activity";
    }
  }

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}`}>{brand.name}</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Audit Trail</span>
      </nav>

      <div>
        <h1 className="page-title">Audit Trail</h1>
        <p className="page-subtitle">Recent pipeline activity for this brand.</p>
      </div>

      {loadError && <div className="alert alert-danger">{loadError}</div>}

      {!loadError && entries.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: "56px 24px" }}>
          <p className="meta">No activity recorded for this brand.</p>
        </div>
      )}

      {!loadError && entries.length > 0 && (
        <div style={{ position: "relative" }}>
          <div style={{ position: "absolute", left: 15, top: 0, bottom: 0, width: 2, background: "var(--border)" }} />

          {entries.map((entry) => (
            <div key={entry.id} style={{ position: "relative", paddingLeft: 40, marginBottom: 16 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: dotColor(entry.status),
                  position: "absolute",
                  left: 11,
                  top: 16,
                }}
              />
              <div className="card-flat" style={{ padding: "14px 18px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                  <span style={{ fontSize: "0.8125rem", fontWeight: 600 }}>{TYPE_LABEL[entry.job_type] ?? entry.job_type}</span>
                  <JobStatusBadge status={entry.status} />
                  <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{entry.stage ?? "—"}</span>
                  <span className="meta" style={{ marginLeft: "auto" }}>{formatDate(entry.created_at)}</span>
                </div>
                <Link
                  className="pill-link"
                  href={`/brands/${brand.id}/jobs/${entry.id}`}
                  style={{ fontSize: "0.8125rem", height: 32, marginTop: 10 }}
                >
                  View run →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
