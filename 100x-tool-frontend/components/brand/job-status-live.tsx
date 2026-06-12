"use client";

import { useEffect, useRef, useState } from "react";

import { getJob } from "@/lib/api";
import type { JobRead } from "@/lib/types";

const POLL_INTERVAL_MS = 3_000;
const ACTIVE_STATUSES = new Set(["QUEUED", "NEW", "RUNNING", "PROCESSING", "SCHEDULED", "GENERATING", "WRITING"]);
const DONE_STATUSES = new Set(["SUCCEEDED", "COMPLETED", "PUBLISHED"]);

// Generic pipeline stage progression (keyword → serp → content → draft).
const stageOrder = ["KEYWORD", "SERP", "CONTENT", "DRAFT", "IMAGE", "COMPLETE"];

function isActive(status: string | null | undefined): boolean {
  return ACTIVE_STATUSES.has((status ?? "").toUpperCase());
}

export function JobStatusLive({
  jobId,
  initial,
  variant = "full",
}: {
  jobId: string;
  initial: JobRead | null;
  variant?: "full" | "compact";
}) {
  const [job, setJob] = useState<JobRead | null>(initial);
  const [error, setError] = useState<string | null>(null);
  const stopRef = useRef(false);

  useEffect(() => {
    stopRef.current = false;

    async function tick() {
      try {
        const next = await getJob(jobId);
        setJob(next);
        setError(null);
        if (!isActive(next.status)) stopRef.current = true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "polling error");
      }
    }

    if (initial && !isActive(initial.status)) return;
    void tick();

    const handle = setInterval(() => {
      if (stopRef.current) { clearInterval(handle); return; }
      void tick();
    }, POLL_INTERVAL_MS);

    return () => { stopRef.current = true; clearInterval(handle); };
  }, [jobId, initial]);

  if (!job) return <p className="meta">Job not found.</p>;

  if (variant === "compact") {
    const stageIdx = stageOrder.indexOf((job.stage ?? "").toUpperCase());
    const pct = DONE_STATUSES.has(job.status.toUpperCase())
      ? 100
      : stageIdx >= 0
        ? Math.round(((stageIdx + 1) / stageOrder.length) * 100)
        : 0;

    return (
      <div className="stack stack-sm">
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 16px", alignItems: "center" }}>
          <span className="meta">Status</span>
          <span style={{ fontSize: "0.875rem", fontWeight: 600, color: job.status === "FAILED" ? "var(--danger)" : DONE_STATUSES.has(job.status.toUpperCase()) ? "var(--success)" : "var(--accent)" }}>
            {job.status}
          </span>
          <span className="meta">Stage</span>
          <span style={{ fontSize: "0.875rem", fontWeight: 500 }}>{job.stage ?? "—"}</span>
        </div>
        {isActive(job.status) && (
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
          </div>
        )}
        {error && <p className="text-danger" style={{ fontSize: "0.8rem" }}>⚠ {error}</p>}
      </div>
    );
  }

  return (
    <div className="card stack">
      <div className="row">
        <h3 style={{ fontSize: "0.9375rem" }}>Job Details</h3>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)" }}>{job.id}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 20px", alignItems: "start" }}>
        {[
          ["Type", job.job_type],
          ["Status", job.status],
          ["Stage", job.stage ?? "—"],
          ["Attempts", `${job.attempt_count} / ${job.max_attempts}`],
          ...(job.error_message ? [["Error", job.error_message]] : []),
        ].map(([k, v]) => (
          <>
            <span key={`k-${k}`} className="meta">{k}</span>
            <span key={`v-${k}`} style={{ fontSize: "0.875rem", color: k === "Error" ? "var(--danger)" : "var(--text)", fontWeight: k === "Status" ? 600 : 400 }}>{v}</span>
          </>
        ))}
      </div>
      {error && <div className="alert alert-danger" style={{ fontSize: "0.8rem" }}>Poll error: {error}</div>}
    </div>
  );
}
