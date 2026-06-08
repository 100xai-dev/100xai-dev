"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getSerpAnalysisResults, startSerpAnalysis, getJob } from "@/lib/api";

type Competitor = {
  url: string;
  title: string;
  content_strength: number | null;
  content_gaps: string[];
  competitive_advantage: string | null;
};

type SerpAnalysis = {
  id: string;
  keyword_text: string;
  status: string;
  total_results_analyzed: number;
  avg_word_count: number | null;
  content_gap_score: number | null;
  created_at: string;
  competitors: Competitor[];
};

type SerpResults = {
  serp_analyses: SerpAnalysis[];
  total_analyses: number;
  latest_job_id: string | null;
  analysis_status: string;
};

function StrengthBar({ value }: { value: number | null }) {
  if (value === null) return <span style={{ color: "var(--gray-400)" }}>—</span>;
  const pct = Math.round(value * 100);
  let color = "#22c55e";
  if (pct < 40) color = "#ef4444";
  else if (pct < 70) color = "#f59e0b";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: "var(--gray-100)", borderRadius: 3 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: "0.75rem", fontWeight: 600, color, minWidth: 32 }}>{pct}%</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; bg: string; color: string }> = {
    COMPLETED: { label: "Completed", bg: "#dcfce7", color: "#15803d" },
    PROCESSING: { label: "Processing…", bg: "#dbeafe", color: "#1d4ed8" },
    FAILED: { label: "Failed", bg: "#fee2e2", color: "#b91c1c" },
    never_run: { label: "Not Started", bg: "#f3f4f6", color: "#6b7280" },
    processing: { label: "Processing…", bg: "#dbeafe", color: "#1d4ed8" },
    completed: { label: "Completed", bg: "#dcfce7", color: "#15803d" },
  };
  const s = map[status] ?? { label: status, bg: "#f3f4f6", color: "#6b7280" };
  return (
    <span style={{ padding: "2px 10px", borderRadius: 999, background: s.bg, color: s.color, fontSize: "0.75rem", fontWeight: 600 }}>
      {s.label}
    </span>
  );
}

export default function SerpAnalysisPage() {
  const params = useParams();
  const brandId = params.id as string;

  const [data, setData] = useState<SerpResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [polling, setPolling] = useState(false);

  const load = async () => {
    try {
      const res = await getSerpAnalysisResults(brandId);
      setData(res);
      // If still processing, keep polling
      if (res.analysis_status === "processing" && res.latest_job_id) {
        setPolling(true);
      } else {
        setPolling(false);
      }
    } catch (err) {
      console.error("Failed to load SERP analysis:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [brandId]);

  // Poll while a job is running
  useEffect(() => {
    if (!polling || !data?.latest_job_id) return;
    const interval = setInterval(async () => {
      try {
        const job = await getJob(data.latest_job_id!);
        if (job.status === "SUCCEEDED" || job.status === "FAILED") {
          clearInterval(interval);
          load();
        }
      } catch { /* ignore */ }
    }, 4000);
    return () => clearInterval(interval);
  }, [polling, data?.latest_job_id]);

  const handleRunAnalysis = async () => {
    setStarting(true);
    try {
      await startSerpAnalysis(brandId);
      await load();
    } catch (err) {
      alert("Failed to start SERP analysis. Make sure keyword research is completed first.");
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <div style={{ width: 24, height: 24, border: "3px solid var(--accent)", borderTop: "3px solid transparent", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto" }} />
        <p style={{ marginTop: 12, color: "var(--gray-500)" }}>Loading SERP analysis…</p>
      </div>
    );
  }

  const analyses = data?.serp_analyses ?? [];
  const status = data?.analysis_status ?? "never_run";

  return (
    <div className="stack stack-lg">
      {/* Breadcrumb */}
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brandId}`}>Brand</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brandId}/keywords`}>Keywords</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>SERP Analysis</span>
      </nav>

      {/* Header */}
      <div className="row" style={{ alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>SERP Analysis</h1>
          <p style={{ color: "var(--gray-500)", marginTop: 4, fontSize: "0.875rem" }}>
            Competitor content intelligence for your top keywords
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <StatusBadge status={status} />
          <Link
            href={`/brands/${brandId}/blogs`}
            style={{
              padding: "8px 16px",
              backgroundColor: "transparent",
              color: "var(--accent)",
              border: "1px solid var(--accent)",
              borderRadius: 6,
              fontWeight: 500,
              fontSize: "0.875rem",
              textDecoration: "none",
            }}
          >
            📝 Blog Engine
          </Link>
          <button
            onClick={handleRunAnalysis}
            disabled={starting || status === "processing"}
            style={{
              padding: "8px 16px",
              backgroundColor: starting || status === "processing" ? "var(--gray-200)" : "var(--accent)",
              color: starting || status === "processing" ? "var(--gray-500)" : "white",
              border: "none",
              borderRadius: 6,
              fontWeight: 500,
              cursor: starting || status === "processing" ? "not-allowed" : "pointer",
              fontSize: "0.875rem",
            }}
          >
            {starting ? "Starting…" : status === "processing" ? "⏳ Running…" : "🔄 Re-run Analysis"}
          </button>
        </div>
      </div>

      {/* Processing banner */}
      {status === "processing" && (
        <div className="card" style={{ borderColor: "var(--accent-border)", background: "var(--accent-light)" }}>
          <div className="row" style={{ alignItems: "center", gap: 10 }}>
            <span className="pulse-dot" style={{ background: "var(--accent)" }} />
            <div>
              <p style={{ fontWeight: 600, color: "var(--accent)" }}>Analysis in Progress</p>
              <p style={{ color: "var(--accent)", fontSize: "0.875rem" }}>
                Crawling competitor pages and running AI analysis. Results appear as each keyword finishes.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Never run */}
      {status === "never_run" && analyses.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: 48 }}>
          <div style={{ fontSize: "3rem", marginBottom: 16 }}>🔍</div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: 8 }}>No SERP Analysis Yet</h3>
          <p style={{ color: "var(--gray-500)", marginBottom: 24, maxWidth: 400, margin: "0 auto 24px" }}>
            Run SERP analysis to discover what competitors are covering for your keywords and find content gaps.
          </p>
          <button
            onClick={handleRunAnalysis}
            disabled={starting}
            style={{
              padding: "10px 24px",
              backgroundColor: "var(--accent)",
              color: "white",
              border: "none",
              borderRadius: 6,
              fontWeight: 600,
              cursor: "pointer",
              fontSize: "0.875rem",
            }}
          >
            {starting ? "Starting…" : "🔍 Start SERP Analysis"}
          </button>
        </div>
      )}

      {/* Summary stats */}
      {analyses.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
          <div className="card" style={{ textAlign: "center" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>{data?.total_analyses ?? 0}</div>
            <div style={{ color: "var(--gray-500)", fontSize: "0.875rem", marginTop: 4 }}>Keywords Analyzed</div>
          </div>
          <div className="card" style={{ textAlign: "center" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>
              {analyses.reduce((s, a) => s + a.total_results_analyzed, 0)}
            </div>
            <div style={{ color: "var(--gray-500)", fontSize: "0.875rem", marginTop: 4 }}>Competitors Crawled</div>
          </div>
          <div className="card" style={{ textAlign: "center" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>
              {Math.round(
                analyses.filter(a => a.avg_word_count).reduce((s, a) => s + (a.avg_word_count ?? 0), 0) /
                  (analyses.filter(a => a.avg_word_count).length || 1)
              ).toLocaleString()}
            </div>
            <div style={{ color: "var(--gray-500)", fontSize: "0.875rem", marginTop: 4 }}>Avg Competitor Words</div>
          </div>
          <div className="card" style={{ textAlign: "center" }}>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>
              {analyses.reduce((s, a) => s + a.competitors.reduce((cs, c) => cs + c.content_gaps.length, 0), 0)}
            </div>
            <div style={{ color: "var(--gray-500)", fontSize: "0.875rem", marginTop: 4 }}>Content Gaps Found</div>
          </div>
        </div>
      )}

      {/* Per-keyword cards */}
      {analyses.map((analysis) => (
        <div key={analysis.id} className="card">
          {/* Keyword header */}
          <div
            className="row"
            style={{ alignItems: "center", justifyContent: "space-between", cursor: "pointer", flexWrap: "wrap", gap: 8 }}
            onClick={() => setExpanded(expanded === analysis.id ? null : analysis.id)}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: "1.25rem" }}>🔑</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: "1rem" }}>{analysis.keyword_text}</div>
                <div style={{ color: "var(--gray-500)", fontSize: "0.8rem", marginTop: 2 }}>
                  {analysis.total_results_analyzed} competitors · Avg {(analysis.avg_word_count ?? 0).toLocaleString()} words
                </div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <StatusBadge status={analysis.status} />
              <Link
                href={`/brands/${brandId}/blogs/new?keyword=${encodeURIComponent(analysis.keyword_text)}`}
                onClick={(e) => e.stopPropagation()}
                style={{
                  padding: "5px 12px",
                  backgroundColor: "var(--accent)",
                  color: "white",
                  borderRadius: 6,
                  fontSize: "0.8rem",
                  fontWeight: 500,
                  textDecoration: "none",
                  whiteSpace: "nowrap",
                }}
              >
                ✍️ Generate Blog
              </Link>
              <span style={{ color: "var(--gray-400)", fontSize: "1.25rem" }}>
                {expanded === analysis.id ? "▲" : "▼"}
              </span>
            </div>
          </div>

          {/* Expanded content */}
          {expanded === analysis.id && (
            <div className="stack stack-md" style={{ marginTop: 20, borderTop: "1px solid var(--border)", paddingTop: 20 }}>

              {/* Competitor table */}
              {analysis.competitors && analysis.competitors.length > 0 ? (
                <div>
                  <h4 style={{ fontWeight: 600, marginBottom: 12, fontSize: "0.9375rem" }}>🏆 Competitor Breakdown</h4>
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                          <th style={{ textAlign: "left", padding: "8px 10px", fontWeight: 600, color: "var(--gray-600)" }}>Page</th>
                          <th style={{ textAlign: "left", padding: "8px 10px", fontWeight: 600, color: "var(--gray-600)", minWidth: 140 }}>Content Strength</th>
                          <th style={{ textAlign: "left", padding: "8px 10px", fontWeight: 600, color: "var(--gray-600)" }}>Competitive Advantage</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.competitors.map((c, i) => (
                          <tr key={i} style={{ borderBottom: "1px solid var(--border-light)" }}>
                            <td style={{ padding: "10px 10px", maxWidth: 280 }}>
                              <div style={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {c.title || new URL(c.url).hostname}
                              </div>
                              <a
                                href={c.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ color: "var(--accent)", fontSize: "0.75rem", textDecoration: "none" }}
                              >
                                {c.url.length > 60 ? c.url.slice(0, 60) + "…" : c.url}
                              </a>
                            </td>
                            <td style={{ padding: "10px 10px", minWidth: 140 }}>
                              <StrengthBar value={c.content_strength} />
                            </td>
                            <td style={{ padding: "10px 10px", color: "var(--gray-600)", fontSize: "0.8125rem" }}>
                              {c.competitive_advantage ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <p style={{ color: "var(--gray-400)", fontSize: "0.875rem" }}>No competitor data available.</p>
              )}

              {/* Content gaps */}
              {analysis.competitors && analysis.competitors.flatMap(c => c.content_gaps).length > 0 && (
                <div>
                  <h4 style={{ fontWeight: 600, marginBottom: 12, fontSize: "0.9375rem" }}>💡 Content Gaps to Exploit</h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {[...new Set(analysis.competitors.flatMap(c => c.content_gaps))].map((gap, i) => (
                      <span
                        key={i}
                        style={{
                          padding: "4px 12px",
                          background: "#fef3c7",
                          color: "#92400e",
                          borderRadius: 999,
                          fontSize: "0.8125rem",
                          border: "1px solid #fde68a",
                        }}
                      >
                        {gap}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
