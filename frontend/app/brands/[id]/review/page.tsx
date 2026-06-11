"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";


interface ReviewItem {
  id: string;
  title: string;
  scheduled_at: string;
  status: string;
  target_keyword: string | null;
  target_channels: string[];
  blog_job_id: string | null;
  draft: {
    title: string;
    meta_description: string | null;
    featured_image_url: string | null;
  };
}


export default function ReviewQueuePage() {
  const params = useParams();
  const brandId = params.id as string;

  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/schedules/brands/${brandId}/review-queue`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      setItems(await res.json());
    } catch (e) {
      setError("Could not load review queue — " + (e instanceof Error ? e.message : "unknown error"));
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => { load(); }, [load]);

  async function act(scheduleId: string, action: "approve" | "reject") {
    setBusy(scheduleId);
    setError(null);
    try {
      const res = await fetch(`/api/v1/schedules/${scheduleId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: action === "reject" ? JSON.stringify({ reason: "Rejected by reviewer" }) : undefined,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : `API error ${res.status}`);
      }
      setItems((prev) => prev.filter((it) => it.id !== scheduleId));
    } catch (e) {
      setError(`Could not ${action} — ` + (e instanceof Error ? e.message : "unknown error"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brandId}`}>Brand</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Review & Publish</span>
      </nav>

      <div>
        <div className="section-heading">Review Queue</div>
        <p className="meta" style={{ marginTop: 4 }}>
          Generated articles awaiting approval. Nothing publishes until you approve it here.
        </p>
      </div>

      {error && (
        <div className="alert alert-warning">
          <span>⚠</span>
          <span>{error} — <button onClick={load} style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", padding: 0 }}>Retry</button></span>
        </div>
      )}

      {loading ? (
        <div className="card" style={{ padding: 24 }}>Loading…</div>
      ) : items.length === 0 ? (
        <div className="card" style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>
          Nothing to review right now. Scheduled articles appear here once generation finishes.
        </div>
      ) : (
        <div className="stack">
          {items.map((it) => (
            <div key={it.id} className="card" style={{ padding: "20px 22px" }}>
              <div className="row" style={{ alignItems: "flex-start", gap: 16 }}>
                {it.draft.featured_image_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={it.draft.featured_image_url} alt="" style={{ width: 96, height: 72, objectFit: "cover", borderRadius: 8, flexShrink: 0 }} />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <h3 style={{ fontSize: "1.0625rem", fontWeight: 700 }}>{it.draft.title || it.title}</h3>
                  {it.draft.meta_description && (
                    <p className="meta" style={{ marginTop: 6 }}>{it.draft.meta_description}</p>
                  )}
                  <div style={{ display: "flex", gap: 14, marginTop: 10, fontSize: "0.8125rem", color: "var(--text-muted)", flexWrap: "wrap" }}>
                    {it.target_keyword && <span>🔑 {it.target_keyword}</span>}
                    <span>📅 {new Date(it.scheduled_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</span>
                    <span>📡 {(it.target_channels ?? []).join(", ") || "wordpress"}</span>
                  </div>
                </div>
              </div>
              <div style={{ marginTop: 16, display: "flex", gap: 10, justifyContent: "flex-end", alignItems: "center" }}>
                {it.blog_job_id && (
                  <Link href={`/brands/${brandId}/blogs/${it.blog_job_id}`} className="pill-link" style={{ fontSize: "0.8125rem", height: 34 }}>Preview article →</Link>
                )}
                <button onClick={() => act(it.id, "reject")} disabled={busy === it.id}
                  style={{ padding: "8px 18px", border: "1px solid #e53935", borderRadius: 6, background: "#fff", fontSize: 13, fontWeight: 500, cursor: busy === it.id ? "default" : "pointer", color: "#b71c1c" }}>Reject</button>
                <button onClick={() => act(it.id, "approve")} disabled={busy === it.id}
                  style={{ padding: "8px 18px", border: "none", borderRadius: 6, background: busy === it.id ? "#a5d6a7" : "#2e7d32", color: "#fff", fontSize: 13, fontWeight: 500, cursor: busy === it.id ? "default" : "pointer" }}>
                  {busy === it.id ? "Working…" : "Approve & Publish"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
