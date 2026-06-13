import Link from "next/link";
import { notFound } from "next/navigation";

import { WordPressSetupForm } from "@/components/brand/wordpress-setup-form";
import { getBrand, listIntegrations } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoBrand } from "@/lib/demo-data";

type PageProps = { params: { id: string } };

export default async function BrandWordpressIntegrationPage({ params }: PageProps) {
  const demo = isDemoMode();

  let brand;
  let siteUrl = "";
  let username = "";
  let status: string | null = null;

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
      const wp = data.items.find((a) => a.provider === "wordpress");
      if (wp) {
        siteUrl = (wp.config?.site_url as string) ?? "";
        username = (wp.config?.username as string) ?? "";
        status = wp.status;
      }
    } catch {
      /* no existing integration — fresh form */
    }
  }

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}`}>{brand.name}</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}/integrations`}>Integrations</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>WordPress</span>
      </nav>

      <div>
        <h1 className="page-title">WordPress Integration</h1>
        <p className="page-subtitle">
          Connect a WordPress site so approved drafts publish straight to it via the REST API.
        </p>
      </div>

      <WordPressSetupForm
        brandId={brand.id}
        initialSiteUrl={siteUrl}
        initialUsername={username}
        currentStatus={status}
      />
    </div>
  );
}
