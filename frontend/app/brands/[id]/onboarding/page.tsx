"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";


interface OnboardingStatus {
  brand_id: string;
  brand_status: string;
  dna_source: string;
  steps: {
    profile_ready: boolean;
    profile_approved: boolean;
    sources_count: number;
    has_sources: boolean;
    has_active_integration: boolean;
    integration_provider: string | null;
    keywords_count: number;
    has_keywords: boolean;
  };
  is_complete: boolean;
  completion: number;
}


export default function OnboardingWizardPage() {
  const params = useParams();
  const brandId = params.id as string;

  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/brands/${brandId}/onboarding-status`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      setStatus(await res.json());
    } catch (e) {
      setError("Could not load setup status — " + (e instanceof Error ? e.message : "unknown error"));
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => { load(); }, [load]);

  const s = status?.steps;
  const steps = [
    {
      title: "Brand DNA",
      desc: status?.dna_source === "manual"
        ? "Fill in your brand profile so generated content stays on-brand."
        : "Review the auto-extracted brand profile and approve it.",
      done: !!s?.profile_ready,
      cta: status?.dna_source === "manual" ? "Edit profile" : "Review DNA",
      href: status?.dna_source === "manual" ? `/brands/${brandId}/dna/manual` : `/brands/${brandId}/dna`,
    },
    {
      title: "Knowledge sources",
      desc: "Add reference URLs or docs to ground content in your brand's knowledge.",
      done: !!s?.has_sources,
      detail: s ? `${s.sources_count} source${s.sources_count === 1 ? "" : "s"}` : undefined,
      cta: "Manage sources",
      href: `/brands/${brandId}/sources`,
    },
    {
      title: "Connect publishing",
      desc: "Connect WordPress (App Password or WordPress.com OAuth) or a webhook to publish.",
      done: !!s?.has_active_integration,
      detail: s?.integration_provider ?? undefined,
      cta: "Connect a channel",
      href: `/brands/${brandId}/integrations`,
    },
    {
      title: "First keyword & publish",
      desc: "Run keyword research, then schedule and review your first article.",
      done: !!s?.has_keywords,
      detail: s ? `${s.keywords_count} keyword${s.keywords_count === 1 ? "" : "s"}` : undefined,
      cta: "Research keywords",
      href: `/brands/${brandId}/keywords`,
    },
  ];

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brandId}`}>Brand</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Setup</span>
      </nav>

      <div>
        <div className="section-heading">Get this brand ready</div>
        <p className="meta" style={{ marginTop: 4 }}>
          Complete these steps to start publishing AI-generated content.
        </p>
      </div>

      {error && (
        <div className="alert alert-warning">
          <span>⚠</span>
          <span>{error} — <button onClick={load} style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", padding: 0 }}>Retry</button></span>
        </div>
      )}

      {/* Progress bar */}
      {status && (
        <div className="card" style={{ padding: "16px 20px" }}>
          <div className="row" style={{ marginBottom: 8 }}>
            <span style={{ fontWeight: 600, fontSize: "0.875rem" }}>Setup {status.completion}% complete</span>
            <span className="meta">{status.is_complete ? "Ready to publish 🎉" : `Status: ${status.brand_status}`}</span>
          </div>
          <div style={{ height: 8, borderRadius: 4, background: "var(--border)", overflow: "hidden" }}>
            <div style={{ width: `${status.completion}%`, height: "100%", background: "var(--accent)", transition: "width 0.3s ease" }} />
          </div>
        </div>
      )}

      {/* Steps */}
      <div className="stack">
        {steps.map((step, i) => (
          <div key={i} className="card" style={{ padding: "18px 20px", opacity: loading ? 0.6 : 1 }}>
            <div className="row" style={{ alignItems: "flex-start", gap: 14 }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "0.8125rem", fontWeight: 700,
                background: step.done ? "#e8f5e9" : "var(--accent-light)",
                color: step.done ? "#2e7d32" : "var(--accent)",
                border: `1.5px solid ${step.done ? "#43a047" : "var(--accent-border)"}`,
              }}>
                {step.done ? "✓" : i + 1}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="row">
                  <h3 style={{ fontSize: "0.9375rem", fontWeight: 700 }}>{step.title}</h3>
                  {step.detail && <span className="meta">{step.detail}</span>}
                </div>
                <p className="meta" style={{ marginTop: 4 }}>{step.desc}</p>
              </div>
              <Link href={step.href} className="pill-link" style={{ fontSize: "0.8125rem", height: 34, whiteSpace: "nowrap" }}>
                {step.cta} →
              </Link>
            </div>
          </div>
        ))}
      </div>

      <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
        <Link href={`/brands/${brandId}`} className="pill-link" style={{ height: 38 }}>Go to brand dashboard →</Link>
      </div>
    </div>
  );
}
