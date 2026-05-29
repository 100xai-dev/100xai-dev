import Link from "next/link";

import { listBrands } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { StatusBadge } from "@/components/brand/status-badge";

const mockBrands = {
  items: [
    { id: "mock-brand-1", name: "Aether Dynamics", website_url: "https://aether-dynamics.io", status: "PENDING_REVIEW" as const, dna_source: "crawl", active_job: { id: "job-101", status: "completed", stage: "extracting", progress: 0 }, channel_readiness: {}, created_by: "", created_at: "", updated_at: "", failure_reason: null },
    { id: "mock-brand-2", name: "Sola Biosystems", website_url: "https://solabio.tech", status: "CRAWLING" as const, dna_source: "crawl", active_job: { id: "job-102", status: "running", stage: "crawling", progress: 0 }, channel_readiness: {}, created_by: "", created_at: "", updated_at: "", failure_reason: null },
    { id: "mock-brand-3", name: "Vesper Heavy Industries", website_url: "https://vesper.heavy.com", status: "READY" as const, dna_source: "manual", active_job: null, channel_readiness: {}, created_by: "", created_at: "", updated_at: "", failure_reason: null },
    { id: "mock-brand-4", name: "Chronos AI Labs", website_url: "https://chronos-ai.org", status: "DRAFT" as const, dna_source: "manual", active_job: null, channel_readiness: {}, created_by: "", created_at: "", updated_at: "", failure_reason: null },
  ],
};

export default async function BrandsPage() {
  const isDemo = isDemoMode();
  const data = isDemo ? mockBrands : await listBrands();

  const total = data.items.length;
  const active = data.items.filter((b) => ["CRAWLING", "EXTRACTING", "INGESTING"].includes(b.status)).length;
  const pending = data.items.filter((b) => b.status === "PENDING_REVIEW").length;
  const ready = data.items.filter((b) => b.status === "READY").length;

  return (
    <div className="stack stack-lg">
      {isDemo && (
        <div className="alert alert-warning">
          <span>⚠</span>
          <span>
            <strong>Demo mode active.</strong> Set <code>API_TOKEN</code> in your environment to connect to the live database.
          </span>
        </div>
      )}

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
        {[
          { label: "Total Brands", value: total, color: "var(--text)" },
          { label: "Processing", value: active, color: "var(--info)" },
          { label: "Pending Review", value: pending, color: "var(--warning)" },
          { label: "Ready", value: ready, color: "var(--success)" },
        ].map((s) => (
          <div key={s.label} className="card card-flat" style={{ padding: "20px 22px", border: "1.5px solid var(--border)" }}>
            <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Page header */}
      <div className="page-head">
        <div>
          <h1 className="page-title">Brands</h1>
          <p className="page-subtitle">Manage client onboarding, DNA extraction and publishing pipelines.</p>
        </div>
        <Link className="topbar-link primary" href="/brands/new" style={{ height: 40, padding: "0 18px", borderRadius: "10px", fontWeight: 500 }}>
          + New Brand
        </Link>
      </div>

      {/* Brands grid */}
      {data.items.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "56px 24px" }}>
          <div style={{ fontSize: "2rem", marginBottom: "12px" }}>✦</div>
          <p style={{ fontWeight: 500, color: "var(--text)" }}>No brands yet</p>
          <p className="meta" style={{ marginTop: 4 }}>Initialize your first brand to get started.</p>
        </div>
      ) : (
        <div className="brand-grid">
          {data.items.map((brand) => (
            <Link key={brand.id} href={`/brands/${brand.id}`} style={{ textDecoration: "none" }}>
              <article className="card brand-card">
                <div className="stack stack-sm">
                  <div className="row" style={{ alignItems: "flex-start" }}>
                    <div>
                      <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 2 }}>{brand.name}</h3>
                      <p className="meta">{brand.website_url ?? "No website"}</p>
                    </div>
                    <StatusBadge status={brand.status} />
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 14, borderTop: "1px solid var(--border)", marginTop: 12 }}>
                  <span className="meta" style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: brand.dna_source === "crawl" ? "var(--info)" : "var(--accent)", display: "inline-block" }} />
                    {brand.dna_source === "crawl" ? "Auto crawl" : "Manual input"}
                  </span>
                  <span style={{ fontSize: "0.8125rem", color: "var(--accent)", fontWeight: 500 }}>
                    Open →
                  </span>
                </div>
              </article>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
