import { notFound } from "next/navigation";

import { ProfileEditor } from "@/components/brand/profile-editor";
import { getBrand, getBrandProfile } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import type { BrandProfileFull } from "@/lib/types";

type PageProps = {
  params: { id: string };
};

const mockBrandDetail = {
  id: "mock-brand-1",
  name: "Aether Dynamics",
  status: "PENDING_REVIEW" as const,
  dna_source: "crawl",
};

const mockProfile: BrandProfileFull = {
  id: "mock-profile-1",
  brand_id: "mock-brand-1",
  name: "Aether Dynamics",
  site_url: "https://aether-dynamics.io",
  one_liner: "Next-generation spatial automation and energy-dense orbital systems for terrestrial expansion.",
  industry: "aerospace",
  tone_rules: "Direct, technically rigorous, highly optimistic about human ingenuity, devoid of modern corporate fluff, slightly industrial.",
  unique_angle: "Synthesizing deep physics with practical automation models, creating a tangible path to self-sustaining spatial infrastructure.",
  allowed_topics: ["Spatial robotics", "Fusion containment", "Orbital logistics", "Kinetic manufacturing"],
  disallowed_topics: ["Crypto speculation", "Hype marketing", "Unbacked sustainability claims"],
  audience_personas: ["Aerospace engineers", "Venture industrialists", "Advanced automation directors"],
  ctas: ["Review telemetry docs", "Schedule a simulator demo", "Join core engineering dev group"],
  banned_phrases: ["disruptive innovation", "paradigm shift", "synergistic ecosystem"],
  proof_points: ["3 completed low-earth orbit validation flights", "99.4% energy efficiency rating on containment systems", "Over 14,000 spatial engineers on our private registry"],
  messaging_guardrails: ["Never guarantee delivery dates for orbital operations", "Always specify weight class restrictions", "Cite physics validations for spatial telemetry"],
  compliance_keywords: ["FAA orbital approval", "FCC licensing", "NASA space safety protocol compliance"],
  image_palette: "#0a0f1d, #00ff66, #7d8794, #ffffff",
  image_subject_hints: "High-contrast telemetry screens, clean laboratory rooms, brushed carbon composite shells, detailed schematic overlays",
  visual_direction: "High contrast tactical layouts, stark dark-mode backgrounds, technical wireframe drawings, monospaced data grids",
  internal_links: [],
  placid_template_id: null,
  image_output_bucket: null,
  default_location: "United States",
  default_language: "English",
  publish_adapter: "none",
  publish_config: {},
  generation_source: "playwright_crawler_v1",
  prompt_version: "v1.4",
  extraction_model: "claude-3-5-sonnet-20241022",
  locked: false,
  locked_at: null,
  locked_by: null,
  created_at: "2026-05-28T00:00:00Z",
  updated_at: "2026-05-28T00:00:00Z",
};

function ProfileRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "8px" }}>
      <span className="meta" style={{ display: "block", marginBottom: "4px" }}>{label}</span>
      <span style={{ fontSize: "0.9rem", lineHeight: "1.5" }}>{value}</span>
    </div>
  );
}

export default async function BrandDnaPage({ params }: PageProps) {
  let brand;
  let profile = null;
  const isDemo = isDemoMode();

  if (isDemo) {
    brand = mockBrandDetail;
    profile = mockProfile;
  } else {
    try {
      brand = await getBrand(params.id);
    } catch {
      notFound();
    }

    try {
      profile = await getBrandProfile(params.id);
    } catch {
      profile = null;
    }
  }

  return (
    <section className="stack">
      {isDemo && (
        <div className="card" style={{ borderColor: "var(--warning)", background: "rgba(255, 179, 0, 0.04)" }}>
          <div className="row" style={{ alignItems: "center" }}>
            <span className="text-success" style={{ color: "var(--warning)", fontFamily: "var(--font-heading)" }}>
              ▲ [SYSTEM_ALERT]: COGNITIVE PROFILE SANDBOX SESSION ACTIVE
            </span>
            <span className="meta" style={{ fontSize: "0.78rem" }}>
              Displaying high-fidelity mock profile. Real operational database connection offline.
            </span>
          </div>
        </div>
      )}

      <div className="meta" style={{ letterSpacing: "0.15em", color: "var(--accent)" }}>
        SYS.NETWORK // BRANDS // {brand.name.toUpperCase().replace(/\s+/g, "_")} // COGNITIVE_DNA
      </div>

      <header className="card stack">
        <div className="row">
          <div>
            <span className="meta" style={{ fontSize: "0.72rem", color: "var(--accent-alt)" }}>
              BIOLOGICAL IDENTITY EXTRACTION
            </span>
            <h2 style={{ marginTop: "4px" }}>Brand DNA Curation</h2>
          </div>
          <span className="status-badge" style={{ color: "var(--accent)", borderColor: "var(--line-strong)", background: "rgba(0, 255, 102, 0.05)" }}>
            PIPELINE_STATUS: {brand.status}
          </span>
        </div>
      </header>

      {!profile ? (
        <section className="card stack" style={{ borderColor: "var(--danger)" }}>
          <p style={{ color: "var(--danger)" }}>[ERROR]: NO EXTRACED COGNITIVE PROFILE DEPLOYED.</p>
          <p className="meta">
            For manual path brands, submit the initial manual DNA schema sheet via the <code>/dna/manual</code> workspace node.
          </p>
        </section>
      ) : (
        <>
          <section className="card stack">
            <h3 style={{ borderBottom: "1px dashed var(--line)", paddingBottom: "10px" }}>
              [COGNITIVE_EXTRACTION_METRICS]
            </h3>
            <div className="grid-2" style={{ gap: "8px 24px" }}>
              <div className="row" style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "6px" }}>
                <span className="meta">EXTRACTION PIPELINE SOURCE:</span>
                <code style={{ color: "var(--accent-alt)" }}>{profile.generation_source.toUpperCase()}</code>
              </div>
              <div className="row" style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "6px" }}>
                <span className="meta">DNA PARSING ENGINE VERSION:</span>
                <code>{profile.prompt_version ?? "v1.0.0-legacy"}</code>
              </div>
              <div className="row" style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "6px" }}>
                <span className="meta">EXTRACTION MODEL SELECTION:</span>
                <code>{profile.extraction_model ?? "n/a"}</code>
              </div>
              <div className="row" style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "6px" }}>
                <span className="meta">IMMUTABILITY STATE (LOCKED):</span>
                <span className="status-badge" style={{
                  color: profile.locked ? "var(--accent)" : "var(--warning)",
                  borderColor: profile.locked ? "var(--line)" : "rgba(255, 179, 0, 0.2)",
                  background: profile.locked ? "rgba(0, 255, 102, 0.05)" : "rgba(255, 179, 0, 0.05)"
                }}>
                  {profile.locked ? "LOCKED (READ-ONLY)" : "UNLOCKED (EDITABLE)"}
                </span>
              </div>
            </div>
          </section>

          {brand.status === "PENDING_REVIEW" && !profile.locked ? (
            <ProfileEditor profile={profile} />
          ) : (
            <>
              {profile.locked && (
                <section className="card" style={{ borderColor: "rgba(255,255,255,0.15)" }}>
                  <div className="row" style={{ alignItems: "center" }}>
                    <span className="meta" style={{ color: "var(--warning)" }}>
                      [SYSTEM_NOTICE]: PROFILE LOCKED — READ-ONLY VIEW
                    </span>
                  </div>
                </section>
              )}
              <section className="card stack">
                <h3 style={{ borderBottom: "1px dashed var(--line)", paddingBottom: "10px" }}>[BRAND_IDENTITY]</h3>
                <ProfileRow label="ONE LINER" value={profile.one_liner} />
                <ProfileRow label="INDUSTRY" value={profile.industry} />
                <ProfileRow label="UNIQUE ANGLE" value={profile.unique_angle} />
                <ProfileRow label="TONE RULES" value={profile.tone_rules} />
              </section>
              <section className="card stack">
                <h3 style={{ borderBottom: "1px dashed var(--line)", paddingBottom: "10px" }}>[AUDIENCE & TOPICS]</h3>
                <ProfileRow label="AUDIENCE PERSONAS" value={(profile.audience_personas ?? []).join(", ")} />
                <ProfileRow label="ALLOWED TOPICS" value={(profile.allowed_topics ?? []).join(", ")} />
                <ProfileRow label="DISALLOWED TOPICS" value={(profile.disallowed_topics ?? []).join(", ")} />
              </section>
              <section className="card stack">
                <h3 style={{ borderBottom: "1px dashed var(--line)", paddingBottom: "10px" }}>[MESSAGING]</h3>
                <ProfileRow label="CTAs" value={(profile.ctas ?? []).join(", ")} />
                <ProfileRow label="PROOF POINTS" value={(profile.proof_points ?? []).join(", ")} />
                <ProfileRow label="BANNED PHRASES" value={(profile.banned_phrases ?? []).join(", ")} />
                <ProfileRow label="MESSAGING GUARDRAILS" value={(profile.messaging_guardrails ?? []).join(", ")} />
                <ProfileRow label="COMPLIANCE KEYWORDS" value={(profile.compliance_keywords ?? []).join(", ")} />
              </section>
              <section className="card stack">
                <h3 style={{ borderBottom: "1px dashed var(--line)", paddingBottom: "10px" }}>[VISUAL_IDENTITY]</h3>
                <ProfileRow label="IMAGE PALETTE" value={profile.image_palette} />
                <ProfileRow label="IMAGE SUBJECT HINTS" value={profile.image_subject_hints} />
                <ProfileRow label="VISUAL DIRECTION" value={profile.visual_direction} />
              </section>
            </>
          )}
        </>
      )}
    </section>
  );
}
