"use client";

import { useMemo, useState } from "react";

import type { KeywordOut } from "@/lib/types";

type SortKey = "related_keyword" | "source_type" | "search_volume" | "keyword_difficulty" | "cpc" | "score";
type SortDir = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "related_keyword", label: "Keyword", numeric: false },
  { key: "source_type", label: "Source", numeric: false },
  { key: "search_volume", label: "Volume", numeric: true },
  { key: "keyword_difficulty", label: "Difficulty", numeric: true },
  { key: "cpc", label: "CPC", numeric: true },
  { key: "score", label: "Score", numeric: true },
];

const thStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  fontWeight: 600,
  color: "var(--text-tertiary)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  padding: "8px 12px",
  borderBottom: "2px solid var(--border)",
  textAlign: "left",
  cursor: "pointer",
  userSelect: "none",
};

const tdStyle: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid var(--border)",
  fontSize: "0.875rem",
};

function scoreColor(score: number): string {
  if (score >= 0.6) return "var(--success)";
  if (score >= 0.3) return "var(--warning)";
  return "var(--danger)";
}

function compare(a: KeywordOut, b: KeywordOut, key: SortKey, dir: SortDir): number {
  const av = a[key];
  const bv = b[key];
  let result: number;
  if (key === "related_keyword" || key === "source_type") {
    result = String(av ?? "").localeCompare(String(bv ?? ""));
  } else {
    // numeric column: nulls sort last regardless of direction
    const an = av === null || av === undefined ? null : Number(av);
    const bn = bv === null || bv === undefined ? null : Number(bv);
    if (an === null && bn === null) return 0;
    if (an === null) return 1;
    if (bn === null) return -1;
    result = an - bn;
  }
  return dir === "asc" ? result : -result;
}

export function JobKeywordsPanel({ initialKeywords }: { initialKeywords: KeywordOut[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    return [...initialKeywords].sort((a, b) => compare(a, b, sortKey, sortDir));
  }, [initialKeywords, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "related_keyword" || key === "source_type" ? "asc" : "desc");
    }
  }

  if (initialKeywords.length === 0) {
    return <p className="meta">No keywords discovered for this brand yet.</p>;
  }

  return (
    <div className="stack">
      <div className="row">
        <div className="section-heading" style={{ margin: 0 }}>Keyword Results</div>
        <span className="status-badge" style={{ color: "var(--accent)", background: "var(--accent-light)", borderColor: "var(--accent-border)" }}>
          {initialKeywords.length} keywords
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  style={{ ...thStyle, textAlign: col.numeric ? "right" : "left" }}
                  onClick={() => toggleSort(col.key)}
                >
                  {col.label}
                  {sortKey === col.key && <span> {sortDir === "asc" ? "▲" : "▼"}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((kw, idx) => (
              <tr key={kw.id} style={{ background: idx % 2 === 1 ? "var(--bg-subtle)" : "transparent" }}>
                <td style={tdStyle}>{kw.related_keyword}</td>
                <td style={tdStyle}>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.7rem",
                      padding: "2px 8px",
                      borderRadius: "var(--radius-full)",
                      background: "var(--bg-subtle)",
                      color: "var(--text-secondary)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    {kw.source_type}
                  </span>
                </td>
                <td style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {kw.search_volume?.toLocaleString("en-IN") ?? "—"}
                </td>
                <td style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {kw.keyword_difficulty ?? "—"}
                </td>
                <td style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {kw.cpc !== null ? `$${kw.cpc.toFixed(2)}` : "—"}
                </td>
                <td style={{ ...tdStyle, textAlign: "right" }}>
                  {kw.score === null ? (
                    "—"
                  ) : (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
                      <span
                        style={{
                          height: 4,
                          borderRadius: "var(--radius-full)",
                          width: `${Math.max(0, Math.min(1, kw.score)) * 100}%`,
                          maxWidth: 60,
                          minWidth: 4,
                          display: "inline-block",
                          verticalAlign: "middle",
                          background: scoreColor(kw.score),
                        }}
                      />
                      <span style={{ fontVariantNumeric: "tabular-nums" }}>{kw.score.toFixed(2)}</span>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
