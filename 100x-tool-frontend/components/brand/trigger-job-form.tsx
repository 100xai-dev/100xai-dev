"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { startKeywordResearch } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { DEMO_COMPLETED_JOB } from "@/lib/demo-data";

export function TriggerJobForm({ brandId, brandName }: { brandId: string; brandName: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(formData: FormData) {
    const seed_keyword = String(formData.get("seed_keyword") ?? "").trim();
    if (!seed_keyword) {
      setError("Seed keyword is required.");
      return;
    }

    setPending(true);
    setError("");

    if (isDemoMode()) {
      // No backend in demo mode — simulate a successful trigger and jump to the
      // fully-populated completed demo job so the output UI is visible.
      setTimeout(() => router.push(`/brands/${brandId}/jobs/${DEMO_COMPLETED_JOB}`), 600);
      return;
    }

    try {
      const response = await startKeywordResearch(brandId, { seed_keyword });
      router.push(`/brands/${brandId}/jobs/${response.job_id}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to start pipeline");
      setPending(false);
    }
  }

  return (
    <form action={onSubmit} style={{ maxWidth: 560, width: "100%" }}>
      <div className="card stack" style={{ padding: "32px" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", marginBottom: 4 }}>Run Pipeline</h2>
          <p className="meta">Seed a new keyword pipeline run for {brandName}.</p>
        </div>

        <hr className="divider" />

        <label>
          Seed Keyword
          <input
            name="seed_keyword"
            required
            placeholder="e.g. project management software"
            style={{ marginTop: 6 }}
          />
          <span className="meta" style={{ marginTop: 2 }}>
            This keyword seeds Pipeline 1. The engine will expand, score, and filter keywords
            before moving to SERP analysis.
          </span>
        </label>

        {error && <div className="alert alert-danger">{error}</div>}

        <div style={{ display: "flex", gap: 10, paddingTop: 4 }}>
          <button type="submit" disabled={pending} style={{ flex: 1 }}>
            {pending ? "Starting…" : "Start Pipeline"}
          </button>
        </div>
      </div>
    </form>
  );
}
