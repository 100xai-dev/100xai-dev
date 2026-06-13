"use client";

import { useState } from "react";

import type { SerpAnalysisItem, SerpCompetitor } from "@/lib/types";

const groupHeaderStyle: React.CSSProperties = {
  fontSize: "0.875rem",
  fontWeight: 600,
  padding: "10px 14px",
  background: "var(--bg-subtle)",
  borderRadius: "var(--radius-md)",
  cursor: "pointer",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

function strengthLabel(value: number | null): string {
  if (value === null) return "—";
  return `${Math.round(value * 100)}%`;
}

function CompetitorCard({ competitor }: { competitor: SerpCompetitor }) {
  return (
    <div className="card-flat" style={{ padding: "14px 16px" }}>
      <a
        href={competitor.url}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          color: "var(--accent)",
          fontSize: "0.8125rem",
          fontFamily: "var(--font-mono)",
          display: "block",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {competitor.url}
      </a>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
        <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text)" }}>
          {competitor.title ?? "Untitled"}
        </span>
        <span
          className="status-badge"
          style={{ color: "var(--text-secondary)", background: "var(--bg-subtle)", borderColor: "var(--border)" }}
        >
          Strength {strengthLabel(competitor.content_strength)}
        </span>
      </div>

      {competitor.competitive_advantage && (
        <div style={{ marginTop: 10 }}>
          <div className="meta">Competitive advantage</div>
          <div style={{ fontSize: "0.875rem", color: "var(--text)" }}>{competitor.competitive_advantage}</div>
        </div>
      )}

      {competitor.content_gaps.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="meta">Content gaps</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
            {competitor.content_gaps.map((gap, i) => (
              <span
                key={i}
                className="status-badge"
                style={{ color: "var(--warning)", background: "var(--warning-light)", borderColor: "var(--warning-border)" }}
              >
                {gap}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Group({ analysis }: { analysis: SerpAnalysisItem }) {
  const [open, setOpen] = useState(false);
  const count = analysis.competitors.length;
  return (
    <div className="stack stack-sm">
      <div
        style={groupHeaderStyle}
        onClick={() => setOpen((o) => !o)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((o) => !o);
          }
        }}
      >
        <span>
          {analysis.keyword_text}{" "}
          <span className="meta" style={{ fontWeight: 400 }}>
            · {count} competitor{count === 1 ? "" : "s"}
            {analysis.avg_word_count ? ` · avg ${analysis.avg_word_count.toLocaleString("en-IN")} words` : ""}
            {analysis.content_gap_score !== null
              ? ` · opportunity ${Math.round(analysis.content_gap_score * 100)}%`
              : ""}
          </span>
        </span>
        <span style={{ color: "var(--text-tertiary)" }}>{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <div className="stack stack-sm">
          {analysis.competitors.map((c, i) => (
            <CompetitorCard key={`${analysis.id}-${i}`} competitor={c} />
          ))}
        </div>
      )}
    </div>
  );
}

export function JobSerpPanel({ initialRecords }: { initialRecords: SerpAnalysisItem[] }) {
  if (initialRecords.length === 0) {
    return <p className="meta">No SERP analysis data for this brand yet.</p>;
  }

  const totalCompetitors = initialRecords.reduce((sum, a) => sum + a.competitors.length, 0);

  return (
    <div className="stack">
      <div className="row">
        <div className="section-heading" style={{ margin: 0 }}>SERP Analysis</div>
        <span className="status-badge" style={{ color: "var(--accent)", background: "var(--accent-light)", borderColor: "var(--accent-border)" }}>
          {totalCompetitors} competitor pages analysed
        </span>
      </div>

      <div className="stack stack-sm">
        {initialRecords.map((analysis) => (
          <Group key={analysis.id} analysis={analysis} />
        ))}
      </div>
    </div>
  );
}
