"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { createBlogJob } from "@/lib/api";

const INTENT_TIPS = [
  "AI tools for small business marketing",
  "how to write SEO blog posts that rank",
  "best content marketing strategies 2026",
];

export default function NewBlogPage() {
  const params = useParams();
  const router = useRouter();
  const brandId = params.id as string;

  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

  return (
    <section className="stack">
      <div className="meta" style={{ letterSpacing: "0.15em", color: "var(--accent)" }}>
        SYS.NETWORK // BLOG_ENGINE // NEW_ARTICLE
      </div>

      <div className="card stack" style={{ maxWidth: 600 }}>
        <h2 style={{ margin: 0 }}>New Article</h2>
        <p className="meta">
          Enter your target keyword. The pipeline will research SERP data, generate a brief + outline,
          then write the full SEO + AEO optimised article using your Brand DNA.
        </p>

        <form className="stack" onSubmit={handleSubmit}>
          <label>
            Target keyword
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="e.g. AI marketing tools for startups"
              autoFocus
              required
            />
          </label>

          <div>
            <div className="meta" style={{ marginBottom: 8 }}>Examples:</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {INTENT_TIPS.map((tip) => (
                <button
                  key={tip}
                  type="button"
                  className="status-badge"
                  style={{ cursor: "pointer", fontSize: "0.78rem" }}
                  onClick={() => setKeyword(tip)}
                >
                  {tip}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-danger" role="alert">{error}</p>}

          <div style={{ background: "rgba(0,255,102,0.04)", border: "1px solid rgba(0,255,102,0.15)", borderRadius: 6, padding: "12px 16px" }}>
            <div className="meta" style={{ fontSize: "0.78rem" }}>
              [PIPELINE] SERP research → Brief + outline → Section writing → Article assembly
            </div>
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Starting pipeline..." : "Generate Article"}
          </button>
        </form>
      </div>
    </section>
  );
}
