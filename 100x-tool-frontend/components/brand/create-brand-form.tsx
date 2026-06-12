"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createBrand } from "@/lib/api";
import type { DnaSource } from "@/lib/types";

export function CreateBrandForm() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string>("");
  const [dnaSource, setDnaSource] = useState<DnaSource>("crawl");

  async function onSubmit(formData: FormData) {
    const name = String(formData.get("name") ?? "").trim();
    const website_url = String(formData.get("website_url") ?? "").trim();
    const dna_source = String(formData.get("dna_source") ?? "crawl") as DnaSource;

    if (!name) { setError("Brand name is required."); return; }
    if (dna_source === "crawl" && !website_url) { setError("Website URL is required for automatic crawl."); return; }

    setPending(true);
    setError("");
    try {
      const response = await createBrand({ name, website_url: website_url || undefined, dna_source });
      router.push(`/brands/${response.brand_id}/onboarding`);
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to create brand");
    } finally {
      setPending(false);
    }
  }

  return (
    <form action={onSubmit} style={{ maxWidth: 560, width: "100%" }}>
      <div className="card stack" style={{ padding: "32px" }}>
        <div>
          <h2 style={{ fontSize: "1.25rem", marginBottom: 4 }}>New Brand</h2>
          <p className="meta">Set up a new brand profile for AI-powered content generation.</p>
        </div>

        <hr className="divider" />

        <label>
          Brand name
          <input
            name="name"
            required
            placeholder="e.g. Acme Corp"
            style={{ marginTop: 6 }}
          />
        </label>

        <label>
          Website URL
          <input
            name="website_url"
            type="url"
            placeholder="https://example.com"
            style={{ marginTop: 6 }}
          />
          <span className="meta" style={{ marginTop: 2 }}>Required for automatic DNA extraction via crawl.</span>
        </label>

        <div>
          <div className="label" style={{ marginBottom: 10 }}>DNA Source</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {([
              { value: "crawl", title: "Auto Crawl", desc: "Crawl the website and extract brand DNA automatically via AI." },
              { value: "manual", title: "Manual Input", desc: "Fill in the brand profile form yourself." },
            ] as { value: DnaSource; title: string; desc: string }[]).map((opt) => (
              <label
                key={opt.value}
                style={{
                  flexDirection: "column",
                  gap: 4,
                  padding: "14px 16px",
                  border: `1.5px solid ${dnaSource === opt.value ? "var(--accent)" : "var(--border)"}`,
                  borderRadius: "var(--radius-lg)",
                  background: dnaSource === opt.value ? "var(--accent-light)" : "var(--bg-white)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                onClick={() => setDnaSource(opt.value)}
              >
                <input
                  name="dna_source"
                  type="radio"
                  value={opt.value}
                  defaultChecked={opt.value === "crawl"}
                  style={{ display: "none" }}
                  readOnly
                />
                <span style={{ fontWeight: 600, fontSize: "0.875rem", color: dnaSource === opt.value ? "var(--accent)" : "var(--text)" }}>
                  {opt.title}
                </span>
                <span className="meta" style={{ fontSize: "0.775rem" }}>{opt.desc}</span>
              </label>
            ))}
          </div>
        </div>

        {error && (
          <div className="alert alert-danger">{error}</div>
        )}

        <div style={{ display: "flex", gap: 10, paddingTop: 4 }}>
          <button type="submit" disabled={pending} style={{ flex: 1 }}>
            {pending ? "Creating brand…" : "Create Brand"}
          </button>
        </div>
      </div>
    </form>
  );
}
