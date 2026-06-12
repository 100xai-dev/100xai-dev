"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { addBrandSource, listBrandSources, reingestSources } from "@/lib/api";
import type { BrandSource, BrandStatus } from "@/lib/types";

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

const SOURCE_LABEL: Record<string, string> = {
  manual_text: "Manual text",
  uploaded_doc: "Uploaded doc",
  crawled_page: "Crawled page",
};

export function SourcesManager({
  brandId,
  brandStatus,
  initialSources,
}: {
  brandId: string;
  brandStatus: BrandStatus;
  initialSources: BrandSource[];
}) {
  const router = useRouter();
  const [sources, setSources] = useState<BrandSource[]>(initialSources);
  const [title, setTitle] = useState("");
  const [rawText, setRawText] = useState("");
  const [adding, setAdding] = useState(false);
  const [reingesting, setReingesting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Backend only accepts new sources while the brand is still editable.
  const canAdd = brandStatus === "DRAFT" || brandStatus === "PENDING_REVIEW";

  async function refresh() {
    try {
      const data = await listBrandSources(brandId);
      setSources(data.items);
    } catch {
      /* keep existing list on refresh failure */
    }
  }

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    const text = rawText.trim();
    if (!text) {
      setError("Paste some text to add as a source.");
      return;
    }
    setAdding(true);
    setError("");
    setNotice("");
    try {
      await addBrandSource(brandId, {
        source_type: "manual_text",
        title: title.trim() || null,
        raw_text: text,
      });
      setTitle("");
      setRawText("");
      setNotice("Source added.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add source");
    } finally {
      setAdding(false);
    }
  }

  async function onReingest() {
    setReingesting(true);
    setError("");
    setNotice("");
    try {
      const res = await reingestSources(brandId);
      setNotice(`Re-ingest started for ${res.sources_count} source(s). Job ${res.job_id.slice(0, 8)}…`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start re-ingest");
    } finally {
      setReingesting(false);
    }
  }

  return (
    <div className="stack stack-lg">
      <div className="page-head">
        <div>
          <h1 className="page-title">Knowledge Sources</h1>
          <p className="page-subtitle">
            Extra context the pipeline grounds content on, beyond the website crawl.
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          onClick={onReingest}
          disabled={reingesting || sources.length === 0}
        >
          {reingesting ? "Re-ingesting…" : "Re-embed into Pinecone"}
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {/* Add manual source */}
      {canAdd ? (
        <form className="card stack" onSubmit={onAdd}>
          <div className="section-heading" style={{ margin: 0 }}>Add a text source</div>
          <label>
            Title (optional)
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Founder interview, product FAQ"
              style={{ marginTop: 6 }}
            />
          </label>
          <label>
            Content
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste brand context, messaging notes, transcripts…"
              style={{ marginTop: 6, minHeight: 140, resize: "vertical", lineHeight: 1.6 }}
            />
          </label>
          <div style={{ paddingTop: 4 }}>
            <button type="submit" disabled={adding}>
              {adding ? "Adding…" : "Add Source"}
            </button>
          </div>
        </form>
      ) : (
        <div className="alert alert-info">
          <span>ℹ</span>
          <span>
            New sources can only be added while the brand is in DRAFT or PENDING_REVIEW. This brand is{" "}
            <strong>{brandStatus}</strong> — use “Re-embed into Pinecone” to re-index existing sources.
          </span>
        </div>
      )}

      {/* Source list */}
      <div className="stack stack-sm">
        <div className="row">
          <div className="section-heading" style={{ margin: 0 }}>Existing sources</div>
          <span className="status-badge" style={{ color: "var(--text-secondary)", background: "var(--bg-subtle)" }}>
            {sources.length} total
          </span>
        </div>

        {sources.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: "40px 24px" }}>
            <p className="meta">No knowledge sources yet.</p>
          </div>
        ) : (
          sources.map((s) => (
            <div key={s.id} className="card-flat" style={{ padding: "14px 18px", display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
              <span className="status-badge" style={{ color: "var(--text-secondary)", background: "var(--bg-subtle)" }}>
                {SOURCE_LABEL[s.source_type] ?? s.source_type}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {s.title || s.url || "Untitled source"}
                </div>
                <div className="meta">
                  {s.word_count != null ? `${s.word_count.toLocaleString("en-IN")} words · ` : ""}
                  {formatDate(s.created_at)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
