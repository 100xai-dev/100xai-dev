"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";
import Link from "next/link";

import { createBlogJob, listKeywords, getSerpAnalysisResults } from "@/lib/api";

type Keyword = {
  id: string;
  related_keyword: string;
  search_volume: number | null;
  keyword_difficulty: number | null;
  score: number | null;
};

export default function NewBlogPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const brandId = params.id as string;

  // Pre-fill from ?keyword= query param (e.g. when arriving from SERP analysis)
  const [keyword, setKeyword] = useState(searchParams.get("keyword") ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Keywords from P1 + P2
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [serpKeywords, setSerpKeywords] = useState<Set<string>>(new Set());
  const [kwLoading, setKwLoading] = useState(true);

  useEffect(() => {
    async function loadKeywords() {
      try {
        const [kwData, serpData] = await Promise.allSettled([
          listKeywords(brandId, 50),
          getSerpAnalysisResults(brandId),
        ]);

        if (kwData.status === "fulfilled") {
          // Sort by score desc, show top 20
          const sorted = [...kwData.value.keywords]
            .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
            .slice(0, 20);
          setKeywords(sorted);
        }

        if (serpData.status === "fulfilled") {
          // Build a set of keywords that have been SERP-analyzed
          const analyzed = new Set(
            serpData.value.serp_analyses.map((a) => a.keyword_text.toLowerCase())
          );
          setSerpKeywords(analyzed);
        }
      } catch {
        // silently ignore — keyword list is optional
      } finally {
        setKwLoading(false);
      }
    }
    loadKeywords();
  }, [brandId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!keyword.trim()) { setError("Enter a keyword"); return; }
    setLoading(true);
    setError("");
    try {
      const job = await createBlogJob(brandId, keyword.trim());
      router.push(`/brands/${brandId}/blogs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create blog job");
      setLoading(false);
    }
  }

  const hasSerpData = (kw: string) => serpKeywords.has(kw.toLowerCase());

  return (
    <section className="stack">
      <div className="meta" style={{ letterSpacing: "0.15em", color: "var(--accent)" }}>
        SYS.NETWORK // BLOG_ENGINE // NEW_ARTICLE
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
        {/* Left: form */}
        <div className="card stack">
          <div>
            <h2 style={{ margin: 0 }}>New Article</h2>
            <p className="meta" style={{ marginTop: 4 }}>
              Enter or pick a keyword. The pipeline will generate a brief + outline,
              then write the full SEO + AEO optimised article using your Brand DNA.
            </p>
          </div>

          <form className="stack" onSubmit={handleSubmit}>
            <label>
              Target keyword
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="e.g. cloud computing services"
                autoFocus
                required
              />
            </label>

            {error && <p className="text-danger" role="alert">{error}</p>}

            <div style={{ background: "rgba(0,255,102,0.04)", border: "1px solid rgba(0,255,102,0.15)", borderRadius: 6, padding: "12px 16px" }}>
              <div className="meta" style={{ fontSize: "0.78rem" }}>
                [PIPELINE] Brand DNA + SERP intelligence → Brief + outline → Section writing → Article assembly
              </div>
            </div>

            <button type="submit" disabled={loading || !keyword.trim()}>
              {loading ? "Starting pipeline..." : "Generate Article"}
            </button>
          </form>
        </div>

        {/* Right: keyword picker */}
        <div className="card stack">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 600 }}>Pick a Researched Keyword</h3>
              <p className="meta" style={{ marginTop: 2, fontSize: "0.8rem" }}>
                From your keyword research. 🔍 = SERP analysis done.
              </p>
            </div>
            <Link href={`/brands/${brandId}/keywords`} style={{ fontSize: "0.78rem", color: "var(--accent)" }}>
              + More keywords
            </Link>
          </div>

          {kwLoading ? (
            <div style={{ textAlign: "center", padding: 24 }}>
              <div style={{ width: 20, height: 20, border: "2px solid var(--accent)", borderTop: "2px solid transparent", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto" }} />
              <p className="meta" style={{ marginTop: 8 }}>Loading keywords...</p>
            </div>
          ) : keywords.length === 0 ? (
            <div style={{ textAlign: "center", padding: 24 }}>
              <p className="meta">No keywords yet.</p>
              <Link href={`/brands/${brandId}/keywords`} className="button" style={{ display: "inline-block", marginTop: 8, fontSize: "0.85rem" }}>
                Run Keyword Research →
              </Link>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 420, overflowY: "auto" }}>
              {keywords.map((kw) => {
                const isSelected = keyword.toLowerCase() === kw.related_keyword.toLowerCase();
                const hasSERP = hasSerpData(kw.related_keyword);
                return (
                  <button
                    key={kw.id}
                    type="button"
                    onClick={() => setKeyword(kw.related_keyword)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 12px",
                      background: isSelected ? "var(--accent)" : "var(--surface)",
                      border: `1px solid ${isSelected ? "var(--accent)" : "var(--border)"}`,
                      borderRadius: 6,
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.15s",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1 }}>
                      {hasSERP && (
                        <span title="SERP analysis completed" style={{ fontSize: "0.75rem" }}>🔍</span>
                      )}
                      <span style={{
                        fontSize: "0.875rem",
                        fontWeight: 500,
                        color: isSelected ? "white" : "var(--text)",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}>
                        {kw.related_keyword}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 8, flexShrink: 0, marginLeft: 8 }}>
                      {kw.search_volume && (
                        <span style={{
                          fontSize: "0.7rem",
                          color: isSelected ? "rgba(255,255,255,0.8)" : "var(--gray-500)",
                        }}>
                          {kw.search_volume >= 1000 ? `${Math.round(kw.search_volume / 1000)}k` : kw.search_volume} vol
                        </span>
                      )}
                      {kw.keyword_difficulty && (
                        <span style={{
                          fontSize: "0.7rem",
                          padding: "1px 6px",
                          borderRadius: 999,
                          background: isSelected
                            ? "rgba(255,255,255,0.2)"
                            : kw.keyword_difficulty >= 70 ? "#fee2e2" : kw.keyword_difficulty >= 50 ? "#fef3c7" : "#dcfce7",
                          color: isSelected
                            ? "white"
                            : kw.keyword_difficulty >= 70 ? "#b91c1c" : kw.keyword_difficulty >= 50 ? "#92400e" : "#15803d",
                        }}>
                          KD {kw.keyword_difficulty}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
