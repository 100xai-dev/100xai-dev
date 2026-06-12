"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { SchedulerProvider, useScheduler, useBrandData } from "@/lib/scheduler/context";
import type { BrandData } from "@/lib/api";


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

// Brand Persona Form Component
function BrandPersonaForm({ brandId, onComplete }: { brandId: string; onComplete: () => void }) {
  const { state, saveBrandData } = useScheduler();
  const { brandData, isLoading, error } = useBrandData(brandId);
  
  const [formData, setFormData] = useState<BrandData>({
    name: '',
    domain: '',
    url: '',
    one: '',
    aud: '',
    tone: [],
    founder: '',
    role: '',
    mission: '',
    accent: '#F58000',
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);

  // Load existing brand data into form
  useEffect(() => {
    if (brandData) {
      setFormData(brandData);
    }
  }, [brandData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await saveBrandData(formData);
      onComplete();
      setShowForm(false);
    } catch (error) {
      console.error('Failed to save brand persona:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToneTagAdd = (tag: string) => {
    if (tag && !formData.tone.includes(tag)) {
      setFormData(prev => ({ ...prev, tone: [...prev.tone, tag] }));
    }
  };

  const handleToneTagRemove = (tag: string) => {
    setFormData(prev => ({ ...prev, tone: prev.tone.filter(t => t !== tag) }));
  };

  const suggestedTones = ['Professional', 'Friendly', 'Technical', 'Creative', 'Authoritative', 'Conversational', 'Educational', 'Inspirational'];

  if (!showForm) {
    return (
      <div className="card" style={{ padding: "18px 20px" }}>
        <div className="row" style={{ alignItems: "flex-start", gap: 14 }}>
          <div style={{
            width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "0.8125rem", fontWeight: 700,
            background: brandData ? "#e8f5e9" : "var(--accent-light)",
            color: brandData ? "#2e7d32" : "var(--accent)",
            border: `1.5px solid ${brandData ? "#43a047" : "var(--accent-border)"}`,
          }}>
            {brandData ? "✓" : "P"}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="row">
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 700 }}>Brand Persona</h3>
              {brandData && <span className="meta">Configured</span>}
            </div>
            <p className="meta" style={{ marginTop: 4 }}>
              Define your brand's personality, voice, and key messaging for content generation.
            </p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="pill-link"
            style={{ fontSize: "0.8125rem", height: 34, whiteSpace: "nowrap" }}
          >
            {brandData ? "Edit persona" : "Set up persona"} →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: "24px" }}>
      <div className="row" style={{ marginBottom: 20, alignItems: "center" }}>
        <h3 style={{ fontSize: "1.125rem", fontWeight: 700 }}>Brand Persona Setup</h3>
        <button
          onClick={() => setShowForm(false)}
          style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer", color: "var(--text-secondary)" }}
        >
          ×
        </button>
      </div>

      {error && (
        <div className="alert alert-warning" style={{ marginBottom: 20 }}>
          <span>⚠</span>
          <span>Error: {error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="stack">
        <div className="row" style={{ gap: 16 }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Brand Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              required
              style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6 }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Domain</label>
            <input
              type="text"
              value={formData.domain}
              onChange={(e) => setFormData(prev => ({ ...prev, domain: e.target.value }))}
              placeholder="example.com"
              style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6 }}
            />
          </div>
        </div>

        <div>
          <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Website URL</label>
          <input
            type="url"
            value={formData.url}
            onChange={(e) => setFormData(prev => ({ ...prev, url: e.target.value }))}
            placeholder="https://example.com"
            style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6 }}
          />
        </div>

        <div>
          <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>One-Liner *</label>
          <input
            type="text"
            value={formData.one}
            onChange={(e) => setFormData(prev => ({ ...prev, one: e.target.value }))}
            required
            placeholder="What does your brand do in one sentence?"
            style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6 }}
          />
        </div>

        <div>
          <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Target Audience *</label>
          <textarea
            value={formData.aud}
            onChange={(e) => setFormData(prev => ({ ...prev, aud: e.target.value }))}
            required
            placeholder="Describe your ideal customers or audience"
            style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6, minHeight: 80, resize: "vertical" }}
          />
        </div>

        <div>
          <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Tone Tags</label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {formData.tone.map((tag, i) => (
              <span
                key={i}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "4px 8px",
                  background: "var(--accent-light)",
                  color: "var(--accent)",
                  fontSize: "0.8125rem",
                  borderRadius: 4,
                  border: "1px solid var(--accent-border)"
                }}
              >
                {tag}
                <button
                  type="button"
                  onClick={() => handleToneTagRemove(tag)}
                  style={{ background: "none", border: "none", cursor: "pointer", fontSize: "0.75rem" }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {suggestedTones.filter(tone => !formData.tone.includes(tone)).map((tone) => (
              <button
                key={tone}
                type="button"
                onClick={() => handleToneTagAdd(tone)}
                style={{
                  padding: "4px 8px",
                  background: "none",
                  border: "1px solid var(--border)",
                  borderRadius: 4,
                  fontSize: "0.8125rem",
                  cursor: "pointer"
                }}
              >
                + {tone}
              </button>
            ))}
          </div>
        </div>

        <div className="row" style={{ gap: 16 }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Founder Name</label>
            <input
              type="text"
              value={formData.founder}
              onChange={(e) => setFormData(prev => ({ ...prev, founder: e.target.value }))}
              style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6 }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Founder Role</label>
            <input
              type="text"
              value={formData.role}
              onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value }))}
              placeholder="CEO, Founder, etc."
              style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6 }}
            />
          </div>
        </div>

        <div>
          <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Mission Statement</label>
          <textarea
            value={formData.mission}
            onChange={(e) => setFormData(prev => ({ ...prev, mission: e.target.value }))}
            placeholder="What is your brand's mission or purpose?"
            style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6, minHeight: 80, resize: "vertical" }}
          />
        </div>

        <div>
          <label style={{ display: "block", marginBottom: 6, fontSize: "0.875rem", fontWeight: 600 }}>Accent Color</label>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <input
              type="color"
              value={formData.accent}
              onChange={(e) => setFormData(prev => ({ ...prev, accent: e.target.value }))}
              style={{ width: 40, height: 40, border: "1px solid var(--border)", borderRadius: 6 }}
            />
            <input
              type="text"
              value={formData.accent}
              onChange={(e) => setFormData(prev => ({ ...prev, accent: e.target.value }))}
              placeholder="#F58000"
              style={{ flex: 1, padding: "8px 12px", border: "1px solid var(--border)", borderRadius: 6 }}
            />
          </div>
        </div>

        <div className="row" style={{ justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
          <button
            type="button"
            onClick={() => setShowForm(false)}
            style={{ padding: "8px 16px", background: "none", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer" }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              padding: "8px 16px",
              background: "var(--accent)",
              color: "white",
              border: "none",
              borderRadius: 6,
              cursor: isSubmitting ? "not-allowed" : "pointer",
              opacity: isSubmitting ? 0.6 : 1
            }}
          >
            {isSubmitting ? "Saving..." : "Save Persona"}
          </button>
        </div>
      </form>
    </div>
  );
}


function OnboardingContent({ brandId }: { brandId: string }) {
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

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

  const handlePersonaComplete = () => {
    setRefreshKey(prev => prev + 1);
  };

  const s = status?.steps;
  const steps = [
    // Brand Persona step (new first step)
    {
      component: () => <BrandPersonaForm brandId={brandId} onComplete={handlePersonaComplete} />,
      isPersona: true,
    },
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
        {steps.map((step, i) => {
          // Handle persona component separately
          if (step.isPersona) {
            return <div key={`persona-${refreshKey}`}>{step.component()}</div>;
          }
          
          return (
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
                  {step.done ? "✓" : i}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="row">
                    <h3 style={{ fontSize: "0.9375rem", fontWeight: 700 }}>{step.title}</h3>
                    {step.detail && <span className="meta">{step.detail}</span>}
                  </div>
                  <p className="meta" style={{ marginTop: 4 }}>{step.desc}</p>
                </div>
                <Link href={step.href || '#'} className="pill-link" style={{ fontSize: "0.8125rem", height: 34, whiteSpace: "nowrap" }}>
                  {step.cta} →
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
        <Link href={`/brands/${brandId}`} className="pill-link" style={{ height: 38 }}>Go to brand dashboard →</Link>
      </div>
    </div>
  );
}

export default function OnboardingWizardPage() {
  const params = useParams();
  const brandId = params.id as string;

  return (
    <SchedulerProvider>
      <OnboardingContent brandId={brandId} />
    </SchedulerProvider>
  );
}
