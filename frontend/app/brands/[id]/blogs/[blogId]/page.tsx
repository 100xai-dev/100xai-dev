"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { approveBrief, approveArticle, getBlogJob, rejectBrief, rejectArticle, retryBlogJob } from "@/lib/api";
import type { BlogJobOut } from "@/lib/types";

const ACTIVE = new Set(["NEW", "RESEARCHING", "BRIEFING", "WRITING", "PUBLISHING"]);

function Score({ label, value }: { label: string; value: number }) {
  const color = value >= 70 ? "var(--accent)" : value >= 40 ? "var(--warning)" : "var(--danger)";
  return (
    <div className="card" style={{ textAlign: "center", flex: 1 }}>
      <div className="meta" style={{ marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: "1.8rem", fontWeight: 700, color }}>{value}</div>
      <div className="meta" style={{ fontSize: "0.72rem" }}>/100</div>
    </div>
  );
}

export default function BlogJobPage() {
  const params = useParams();
  const router = useRouter();
  const brandId = params.id as string;
  const jobId = params.blogId as string;

  const [job, setJob] = useState<BlogJobOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState("");
  const [selectedTitle, setSelectedTitle] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const selectedTitleRef = useRef(selectedTitle);
  selectedTitleRef.current = selectedTitle;

  const fetchJob = useCallback(async () => {
    try {
      const data = await getBlogJob(brandId, jobId);
      setJob(data);
      // Only set selectedTitle once when the brief first arrives — use ref to avoid
      // making selectedTitle a dep of fetchJob (which would restart the interval on every
      // title radio-button click).
      if (data.brief?.selected_title && !selectedTitleRef.current) {
        setSelectedTitle(data.brief.selected_title);
      }
    } catch {
      setError("Failed to load job");
    } finally {
      setLoading(false);
    }
  }, [brandId, jobId]); // ← selectedTitle intentionally removed from deps

  useEffect(() => {
    void fetchJob();

    // Poll every 3 s while the job is in an active state.
    // Call fetchJob directly from the interval — don't use setState as a side-effect trigger.
    intervalRef.current = setInterval(() => {
      setJob((prev) => {
        if (prev && ACTIVE.has(prev.status)) {
          void fetchJob();
        } else {
          clearInterval(intervalRef.current!);
          intervalRef.current = null;
        }
        return prev; // keep state unchanged; fetchJob's own setJob will update it
      });
    }, 3000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetchJob]); // fetchJob is now stable (no selectedTitle dep) → effect runs once

  async function act(fn: () => Promise<BlogJobOut>) {
    setActing(true); setError("");
    try {
      const updated = await fn();
      setJob(updated);
      // If the action moved the job into an ACTIVE state, restart polling
      if (ACTIVE.has(updated.status)) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        intervalRef.current = setInterval(() => {
          setJob((prev) => {
            if (prev && ACTIVE.has(prev.status)) {
              void fetchJob();
            } else {
              clearInterval(intervalRef.current!);
              intervalRef.current = null;
            }
            return prev;
          });
        }, 3000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActing(false);
    }
  }


  if (loading) return <div className="card meta">Loading...</div>;
  if (!job) return <div className="card meta" style={{ color: "var(--danger)" }}>{error || "Not found"}</div>;

  const isActive = ACTIVE.has(job.status);
  const brief = job.brief;
  const draft = job.draft;

  return (
    <section className="stack">
      <div className="meta" style={{ letterSpacing: "0.15em", color: "var(--accent)" }}>
        SYS.NETWORK // BLOG_ENGINE // {job.keyword.toUpperCase()}
      </div>

      {/* Status header */}
      <div className="card row" style={{ alignItems: "center" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>{brief?.selected_title ?? job.keyword}</div>
          <div className="meta">Keyword: {job.keyword}</div>
        </div>
        <span className="status-badge" style={{
          color: job.status === "PUBLISHED" ? "var(--accent)" : job.status.includes("REVIEW") ? "var(--warning)" : job.status === "FAILED" ? "var(--danger)" : "var(--accent-alt)",
        }}>
          {job.status}
        </span>
      </div>

      {/* Active pipeline indicator */}
      {isActive && (
        <div className="card" style={{ borderColor: "var(--accent-alt)" }}>
          <div className="row" style={{ alignItems: "center", gap: 12 }}>
            <div className="pulse-dot" />
            <span className="meta">Pipeline running — {job.status.replace(/_/g, " ")}...</span>
          </div>
        </div>
      )}

      {/* Error */}
      {job.status === "FAILED" && (
        <div className="card stack" style={{ borderColor: "var(--danger)" }}>
          <p style={{ color: "var(--danger)" }}>
            {job.error_message ?? "An error occurred"}
          </p>
          <button onClick={() => act(() => retryBlogJob(brandId, jobId))} disabled={acting}>
            Retry from beginning
          </button>
        </div>
      )}

      {/* Brief review */}
      {job.status === "PENDING_BRIEF_REVIEW" && brief && (
        <div className="card stack">
          <h3>[BRIEF + OUTLINE] — Review before writing</h3>

          <div>
            <div className="meta" style={{ marginBottom: 8 }}>Title (select or keep)</div>
            {brief.title_options.map((t) => (
              <label key={t} style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 8, cursor: "pointer" }}>
                <input type="radio" name="title" value={t} checked={selectedTitle === t} onChange={() => setSelectedTitle(t)} />
                <span>{t}</span>
              </label>
            ))}
          </div>

          <div>
            <div className="meta">Meta description</div>
            <p style={{ margin: "4px 0", fontSize: "0.9rem" }}>{brief.meta_description}</p>
            <div className="meta" style={{ fontSize: "0.72rem" }}>{brief.meta_description.length} chars</div>
          </div>

          <div className="grid-2" style={{ gap: "8px 24px" }}>
            <div><span className="meta">Intent: </span><code>{brief.search_intent}</code></div>
            <div><span className="meta">Target words: </span><code>{brief.target_word_count}</code></div>
            <div><span className="meta">Audience: </span><span style={{ fontSize: "0.88rem" }}>{brief.target_audience}</span></div>
            <div><span className="meta">Tags: </span><span style={{ fontSize: "0.88rem" }}>{brief.tags.join(", ")}</span></div>
          </div>

          <div>
            <div className="meta" style={{ marginBottom: 8 }}>Outline ({brief.outline.length} sections)</div>
            {brief.outline.map((sec, i) => (
              <div key={i} style={{ borderLeft: "2px solid var(--line)", paddingLeft: 12, marginBottom: 10 }}>
                <div style={{ fontWeight: 500 }}>{sec.heading}</div>
                <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                  {sec.key_points.map((pt: string, j: number) => (
                    <li key={j} className="meta" style={{ fontSize: "0.82rem" }}>{pt}</li>
                  ))}
                </ul>
                <div className="meta" style={{ fontSize: "0.72rem" }}>~{sec.estimated_words} words</div>
              </div>
            ))}
          </div>

          <div>
            <div className="meta" style={{ marginBottom: 4 }}>AEO Direct answer</div>
            <p style={{ fontSize: "0.88rem", background: "rgba(0,255,102,0.04)", padding: "8px 12px", borderRadius: 6, margin: 0 }}>
              {brief.aeo.direct_answer}
            </p>
          </div>

          {brief.aeo.faqs?.length > 0 && (
            <div>
              <div className="meta" style={{ marginBottom: 4 }}>FAQs ({brief.aeo.faqs.length})</div>
              {brief.aeo.faqs.map((faq: { question: string; answer: string }, i: number) => (
                <div key={i} style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: "0.88rem", fontWeight: 500 }}>Q: {faq.question}</div>
                  <div className="meta" style={{ fontSize: "0.82rem" }}>A: {faq.answer}</div>
                </div>
              ))}
            </div>
          )}

          {error && <p className="text-danger">{error}</p>}

          <div className="row" style={{ gap: 12 }}>
            <button
              onClick={() => act(() => approveBrief(brandId, jobId, selectedTitle || undefined))}
              disabled={acting}
              style={{ flex: 1 }}
            >
              {acting ? "Processing..." : "✓ Approve — Start Writing"}
            </button>
            <button
              onClick={() => act(() => rejectBrief(brandId, jobId))}
              disabled={acting}
              style={{ flex: 1, background: "rgba(255,59,48,0.1)", borderColor: "var(--danger)", color: "var(--danger)" }}
            >
              ✗ Reject — Start Over
            </button>
          </div>
        </div>
      )}

      {/* Article review */}
      {job.status === "PENDING_REVIEW" && draft && (
        <div className="card stack">
          <h3>[ARTICLE REVIEW] — Approve or reject</h3>

          <div className="row" style={{ gap: 12 }}>
            <Score label="SEO" value={draft.seo_score} />
            <Score label="AEO" value={draft.aeo_score} />
            <Score label="VIRALITY" value={draft.virality_score} />
            <div className="card" style={{ textAlign: "center", flex: 1 }}>
              <div className="meta" style={{ marginBottom: 4 }}>WORDS</div>
              <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>{draft.word_count}</div>
            </div>
          </div>

          <div>
            <div className="meta" style={{ marginBottom: 4 }}>Title</div>
            <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>{draft.title}</div>
          </div>

          <div>
            <div className="meta" style={{ marginBottom: 4 }}>Meta description</div>
            <p style={{ margin: 0, fontSize: "0.88rem" }}>{draft.meta_description}</p>
          </div>

          <div>
            <div className="meta" style={{ marginBottom: 8 }}>Article content</div>
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--line)",
                borderRadius: 6,
                padding: "16px 20px",
                maxHeight: 600,
                overflowY: "auto",
                fontSize: "0.9rem",
                lineHeight: 1.7,
              }}
              dangerouslySetInnerHTML={{ __html: draft.html_content }}
            />
          </div>

          {error && <p className="text-danger">{error}</p>}

          <div className="row" style={{ gap: 12 }}>
            <button
              onClick={() => act(() => approveArticle(brandId, jobId))}
              disabled={acting}
              style={{ flex: 1 }}
            >
              {acting ? "Processing..." : "✓ Approve & Publish"}
            </button>
            <button
              onClick={() => act(() => rejectArticle(brandId, jobId))}
              disabled={acting}
              style={{ flex: 1, background: "rgba(255,59,48,0.1)", borderColor: "var(--danger)", color: "var(--danger)" }}
            >
              ✗ Reject — Start Over
            </button>
          </div>
        </div>
      )}

      {/* Published */}
      {job.status === "PUBLISHED" && draft && (
        <div className="card stack" style={{ borderColor: "var(--accent)" }}>
          <div style={{ color: "var(--accent)", fontWeight: 600 }}>✓ Article approved and published</div>
          <div className="meta">{draft.word_count} words · SEO {draft.seo_score}/100 · AEO {draft.aeo_score}/100</div>
        </div>
      )}

      {/* Rejected — retry */}
      {job.status === "REJECTED" && (
        <div className="card stack" style={{ borderColor: "var(--warning)" }}>
          <div className="meta">Article rejected. Start over with a new keyword or retry the same one.</div>
          <div className="row" style={{ gap: 12 }}>
            <button onClick={() => act(() => retryBlogJob(brandId, jobId))} disabled={acting}>
              Retry same keyword
            </button>
            <button onClick={() => router.push(`/brands/${brandId}/blogs/new`)}>
              New keyword
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
