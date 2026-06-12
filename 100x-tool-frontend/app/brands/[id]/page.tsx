import Link from "next/link";
import { notFound } from "next/navigation";

import { BrandActions } from "@/components/brand/brand-actions";
import { JobStatusLive } from "@/components/brand/job-status-live";
import { StatusBadge } from "@/components/brand/status-badge";
import { getBrand } from "@/lib/api";
import { isDemoMode } from "@/lib/config";

type PageProps = { params: { id: string } };

const mockBrandsMap: Record<string, any> = {
  "mock-brand-1": { id: "mock-brand-1", name: "Aether Dynamics", website_url: "https://aether-dynamics.io", status: "PENDING_REVIEW", dna_source: "crawl", active_job: { id: "job-101", status: "COMPLETED", stage: "EXTRACTING" } },
  "mock-brand-2": { id: "mock-brand-2", name: "Sola Biosystems", website_url: "https://solabio.tech", status: "CRAWLING", dna_source: "crawl", active_job: { id: "job-102", status: "RUNNING", stage: "CRAWLING" } },
  "mock-brand-3": { id: "mock-brand-3", name: "Vesper Heavy Industries", website_url: "https://vesper.heavy.com", status: "READY", dna_source: "manual", active_job: null },
  "mock-brand-4": { id: "mock-brand-4", name: "Chronos AI Labs", website_url: "https://chronos-ai.org", status: "DRAFT", dna_source: "manual", active_job: null },
};

const tabs = [
  { num: "00", label: "Setup Wizard", href: (id: string) => `/brands/${id}/onboarding` },
  { num: "01", label: "DNA Review & Curation", href: (id: string) => `/brands/${id}/dna` },
  { num: "02", label: "Manual Profile Input", href: (id: string) => `/brands/${id}/dna/manual` },
  { num: "03", label: "Knowledge Base Sources", href: (id: string) => `/brands/${id}/sources` },
<<<<<<< Updated upstream
  { num: "04", label: "Keyword Research", href: (id: string) => `/brands/${id}/keywords` },
  { num: "05", label: "Connected Services", href: (id: string) => `/brands/${id}/integrations` },
  { num: "06", label: "WordPress Engine Setup", href: (id: string) => `/brands/${id}/integrations/wordpress` },
  { num: "07", label: "Operational Params", href: (id: string) => `/brands/${id}/operational` },
  { num: "08", label: "Audit Trail", href: (id: string) => `/brands/${id}/audit` },
  { num: "09", label: "Blog Engine", href: (id: string) => `/brands/${id}/blogs` },
  { num: "10", label: "Content Calendar", href: (id: string) => `/brands/${id}/calendar` },
  { num: "11", label: "Review & Publish", href: (id: string) => `/brands/${id}/review` },
=======
  { num: "04", label: "Connected Services", href: (id: string) => `/brands/${id}/integrations` },
  { num: "05", label: "WordPress Engine Setup", href: (id: string) => `/brands/${id}/integrations/wordpress` },
  { num: "06", label: "Operational Params", href: (id: string) => `/brands/${id}/operational` },
  { num: "07", label: "Audit Trail", href: (id: string) => `/brands/${id}/audit` },
  { num: "08", label: "Run History & Outputs", href: (id: string) => `/brands/${id}/jobs` },
  { num: "09", label: "Content Calendar", href: (id: string) => `/brands/${id}/schedule` },
>>>>>>> Stashed changes
];

export default async function BrandDetailPage({ params }: PageProps) {
  let brand: any;
  const isDemo = isDemoMode();

  if (isDemo) {
    brand = mockBrandsMap[params.id] ?? mockBrandsMap["mock-brand-1"];
  } else {
    try { brand = await getBrand(params.id); } catch { notFound(); }
  }

  return (
    <div className="stack stack-lg">
      {isDemo && (
        <div className="alert alert-warning">
          <span>⚠</span>
          <span><strong>Demo mode.</strong> Displaying mock data.</span>
        </div>
      )}

      {/* Breadcrumb */}
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>{brand.name}</span>
      </nav>

      {/* Brand header card */}
      <div className="card" style={{ padding: "28px 28px 24px" }}>
        <div className="row" style={{ alignItems: "flex-start", gap: 20 }}>
          {/* Avatar / initials */}
          <div style={{
            width: 52, height: 52, borderRadius: 14,
            background: "var(--accent-light)", border: "1.5px solid var(--accent-border)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "1.125rem", fontWeight: 700, color: "var(--accent)", flexShrink: 0,
          }}>
            {brand.name.charAt(0)}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <h2 style={{ fontSize: "1.375rem", fontWeight: 700 }}>{brand.name}</h2>
              <StatusBadge status={brand.status} />
            </div>
            <p className="meta" style={{ marginTop: 4 }}>
              {brand.website_url ?? "No website attached"}
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 24, marginTop: 20, paddingTop: 18, borderTop: "1px solid var(--border)" }}>
          <div>
            <div className="meta">DNA Source</div>
            <div style={{ fontWeight: 600, fontSize: "0.875rem", marginTop: 2, textTransform: "capitalize" }}>
              {brand.dna_source === "crawl" ? "Auto Crawl" : "Manual Input"}
            </div>
          </div>
          <div>
            <div className="meta">Brand ID</div>
            <code style={{ display: "block", marginTop: 2, fontSize: "0.75rem" }}>{brand.id}</code>
          </div>
        </div>
      </div>

      {/* Setup prompt while the brand isn't fully ready */}
      {!isDemo && brand.status !== "READY" && (
        <Link href={`/brands/${brand.id}/onboarding`} className="card" style={{ padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, textDecoration: "none", borderColor: "var(--accent-border)", background: "var(--accent-light)" }}>
          <div>
            <div style={{ fontWeight: 600, color: "var(--accent)" }}>Finish setting up this brand</div>
            <div className="meta" style={{ marginTop: 2 }}>Walk through DNA, sources, publishing and your first article.</div>
          </div>
          <span className="pill-link" style={{ height: 36 }}>Continue setup →</span>
        </Link>
      )}

      {/* Navigation tabs */}
      <div>
        <div className="section-heading">Tools & Configuration</div>
        <div className="tab-grid">
          {tabs.map((tab) => (
            <Link key={tab.num} className="tab-link" href={tab.href(brand.id)}>
              <span className="tab-link-num">{tab.num}</span>
              {tab.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Active job */}
      {brand.active_job && (
        <div className="card" style={{ borderColor: "var(--accent-border)", background: "var(--accent-light)" }}>
          <div className="row" style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="pulse-dot" style={{ background: "var(--accent)" }} />
              <h3 style={{ color: "var(--accent)", fontSize: "0.9375rem" }}>Pipeline Running</h3>
            </div>
            <Link
              className="pill-link"
              href={`/brands/${brand.id}/jobs/${brand.active_job.id}`}
              style={{ fontSize: "0.8125rem", height: 34 }}
            >
              Inspect job →
            </Link>
          </div>
          <JobStatusLive jobId={brand.active_job.id} initial={null} variant="compact" />
        </div>
      )}

      {/* Actions */}
      <BrandActions brand={brand} />
    </div>
  );
}
