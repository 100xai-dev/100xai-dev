import Link from "next/link";
import { notFound } from "next/navigation";

import { getBrand, listIntegrations } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoBrand } from "@/lib/demo-data";
import type { IntegrationAccount } from "@/lib/types";

type PageProps = { params: { id: string } };

type Tone = "success" | "warning" | "danger" | "muted";

const PROVIDERS: {
  provider: string;
  name: string;
  icon: string;
  description: string;
  href?: (id: string) => string;
  live: boolean;
}[] = [
  {
    provider: "wordpress",
    name: "WordPress",
    icon: "W",
    description: "Publish directly to your WordPress site via REST API.",
    href: (id) => `/brands/${id}/integrations/wordpress`,
    live: true,
  },
  { provider: "webflow", name: "Webflow", icon: "≈", description: "Push content to a Webflow CMS collection.", live: false },
  { provider: "shopify", name: "Shopify", icon: "S", description: "Publish blog posts to your Shopify store.", live: false },
  { provider: "webhook", name: "Custom Webhook", icon: "{ }", description: "POST the draft to your own webhook endpoint.", live: false },
];

function statusFor(account: IntegrationAccount | undefined, live: boolean): { label: string; tone: Tone } {
  if (!live) return { label: "Coming soon", tone: "muted" };
  if (!account) return { label: "Not configured", tone: "warning" };
  if (account.status === "active") return { label: "Connected", tone: "success" };
  if (account.status === "failed") return { label: "Connection failed", tone: "danger" };
  return { label: "Configured", tone: "warning" };
}

function pillStyle(tone: Tone): React.CSSProperties {
  switch (tone) {
    case "success":
      return { color: "var(--success)", background: "var(--success-light)", borderColor: "var(--success-border)" };
    case "danger":
      return { color: "var(--danger)", background: "var(--danger-light)", borderColor: "var(--danger-border)" };
    case "warning":
      return { color: "var(--warning)", background: "var(--warning-light)", borderColor: "var(--warning-border)" };
    default:
      return { color: "var(--text-secondary)", background: "var(--bg-subtle)", borderColor: "var(--border)" };
  }
}

export default async function BrandIntegrationsPage({ params }: PageProps) {
  const demo = isDemoMode();

  let brand;
  let accounts: IntegrationAccount[] = [];

  if (demo) {
    brand = demoBrand(params.id);
  } else {
    try {
      brand = await getBrand(params.id);
    } catch {
      notFound();
    }
    try {
      const data = await listIntegrations(params.id);
      accounts = data.items;
    } catch {
      /* render with no live accounts */
    }
  }

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}`}>{brand.name}</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Integrations</span>
      </nav>

      <div>
        <h1 className="page-title">Integrations</h1>
        <p className="page-subtitle">Connect publishing channels for this brand.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
        {PROVIDERS.map((it) => {
          const account = accounts.find((a) => a.provider === it.provider);
          const { label, tone } = statusFor(account, it.live);
          const card = (
            <article className="card" style={{ height: "100%", opacity: it.live ? 1 : 0.7 }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
                <div
                  style={{
                    width: 42,
                    height: 42,
                    borderRadius: 12,
                    background: "var(--bg-subtle)",
                    border: "1px solid var(--border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    color: "var(--text-secondary)",
                    flexShrink: 0,
                  }}
                >
                  {it.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                    <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>{it.name}</h3>
                    <span className="status-badge" style={pillStyle(tone)}>{label}</span>
                  </div>
                  <p className="meta" style={{ marginTop: 4 }}>{it.description}</p>
                  {account?.last_error && tone === "danger" && (
                    <p className="meta" style={{ marginTop: 6, color: "var(--danger)" }}>{account.last_error}</p>
                  )}
                </div>
              </div>
            </article>
          );

          return it.href ? (
            <Link key={it.provider} href={it.href(brand.id)} style={{ textDecoration: "none" }}>
              {card}
            </Link>
          ) : (
            <div key={it.provider} style={{ cursor: "not-allowed" }}>
              {card}
            </div>
          );
        })}
      </div>
    </div>
  );
}
