"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { approveArticle, rejectArticle } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import type { BlogDraftOut } from "@/lib/types";

const ARTICLE_CLASS = "jcp-article-prose";

const pillStyle: React.CSSProperties = {
  fontSize: "0.75rem",
  padding: "4px 10px",
  borderRadius: "var(--radius-full)",
  border: "1px solid var(--border)",
  background: "var(--bg-subtle)",
  color: "var(--text-secondary)",
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  whiteSpace: "nowrap",
};

function scoreTone(score: number): React.CSSProperties {
  if (score >= 70) {
    return { background: "var(--success-light)", color: "var(--success)", borderColor: "var(--success-border)" };
  }
  if (score >= 40) {
    return { background: "var(--warning-light)", color: "var(--warning)", borderColor: "var(--warning-border)" };
  }
  return { background: "var(--danger-light)", color: "var(--danger)", borderColor: "var(--danger-border)" };
}

export function JobContentPanel({
  draft,
  jobId,
  brandId,
}: {
  draft: BlogDraftOut;
  jobId: string;
  brandId: string;
}) {
  const router = useRouter();

  const [copied, setCopied] = useState(false);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function onCopy() {
    if (!draft.html_content) return;
    try {
      await navigator.clipboard.writeText(draft.html_content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable — silently ignore
    }
  }

  async function onApprove() {
    setApproving(true);
    setError("");
    setSuccess("");

    if (isDemoMode()) {
      setTimeout(() => {
        setSuccess("Draft approved and published to WordPress.");
        setApproving(false);
      }, 800);
      return;
    }

    try {
      await approveArticle(brandId, jobId);
      setSuccess("Draft approved and published live to WordPress.");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve & publish draft");
    } finally {
      setApproving(false);
    }
  }

  async function onReject() {
    const confirmed = window.confirm("Reject this draft? It will be marked REJECTED. You can retry generation afterwards.");
    if (!confirmed) return;
    setRejecting(true);
    setError("");
    setSuccess("");

    if (isDemoMode()) {
      setTimeout(() => router.push(`/brands/${brandId}/jobs`), 600);
      return;
    }

    try {
      await rejectArticle(brandId, jobId);
      router.push(`/brands/${brandId}/jobs`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject draft");
      setRejecting(false);
    }
  }

  return (
    <div className="stack">
      {/* A. Metadata strip */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span style={pillStyle}>{draft.title}</span>
        <span style={pillStyle}>{draft.word_count.toLocaleString("en-IN")} words</span>
        <span style={{ ...pillStyle, ...scoreTone(draft.seo_score) }}>SEO {draft.seo_score}</span>
        <span style={{ ...pillStyle, ...scoreTone(draft.aeo_score) }}>AEO {draft.aeo_score}</span>
        <span style={{ ...pillStyle, ...scoreTone(draft.virality_score) }}>Virality {draft.virality_score}</span>
        {draft.approved && (
          <span style={{ ...pillStyle, background: "var(--success-light)", color: "var(--success)", borderColor: "var(--success-border)" }}>
            Published ✓
          </span>
        )}
      </div>

      {/* B. Featured image */}
      <div className="stack stack-sm">
        <div className="meta">Featured Image</div>
        {draft.featured_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={draft.featured_image_url}
            alt={draft.title}
            style={{ maxHeight: 280, borderRadius: "var(--radius-lg)", objectFit: "cover", width: "100%" }}
          />
        ) : (
          <div className="card-flat" style={{ padding: "40px 24px", textAlign: "center", color: "var(--text-tertiary)" }}>
            Image not generated
          </div>
        )}
      </div>

      {/* C. Article preview */}
      {draft.html_content && (
        <div className="stack stack-sm">
          <div className="row">
            <div className="section-heading" style={{ margin: 0 }}>Article Draft</div>
            <button type="button" className="btn-secondary" onClick={onCopy}>
              {copied ? "Copied ✓" : "Copy HTML"}
            </button>
          </div>
          <style>{`
            .${ARTICLE_CLASS} h1 { font-family: var(--serif); font-size: 1.9rem; font-weight: 500; margin: 1.2em 0 .5em; letter-spacing:-.02em; }
            .${ARTICLE_CLASS} h2 { font-family: var(--serif); font-size: 1.4rem; font-weight: 500; margin: 1.4em 0 .5em; }
            .${ARTICLE_CLASS} h3 { font-size: 1.1rem; font-weight: 600; margin: 1.3em 0 .4em; }
            .${ARTICLE_CLASS} p { margin-bottom: 1em; }
            .${ARTICLE_CLASS} ul, .${ARTICLE_CLASS} ol { margin-left: 1.5em; margin-bottom: 1em; }
            .${ARTICLE_CLASS} a { color: var(--accent); }
            .${ARTICLE_CLASS} img { max-width: 100%; border-radius: var(--radius-md); }
          `}</style>
          <div
            className={ARTICLE_CLASS}
            style={{ maxWidth: 760, fontSize: "0.95rem", lineHeight: 1.75, color: "var(--text)" }}
            dangerouslySetInnerHTML={{ __html: draft.html_content }}
          />
        </div>
      )}

      {/* D. Meta description */}
      {draft.meta_description && (
        <div className="stack stack-sm">
          <div className="meta">Meta Description</div>
          <div className="card-flat" style={{ padding: "12px 14px", fontFamily: "var(--font-mono)", fontSize: "0.875rem" }}>
            {draft.meta_description}
          </div>
        </div>
      )}

      {/* E. Decision bar */}
      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {!draft.approved && (
        <div
          style={{
            position: "sticky",
            bottom: 0,
            background: "var(--bg-white)",
            borderTop: "2px solid var(--border)",
            padding: "16px 4px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 24,
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            Approving publishes the article live to the connected WordPress site.
          </span>
          <div style={{ display: "flex", gap: 10 }}>
            <button type="button" className="danger" onClick={onReject} disabled={approving || rejecting}>
              {rejecting ? "Rejecting…" : "Reject"}
            </button>
            <button type="button" onClick={onApprove} disabled={approving || rejecting}>
              {approving ? "Publishing…" : "Approve & Publish →"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
