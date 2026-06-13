import Link from "next/link";
import { notFound } from "next/navigation";

import { SourcesManager } from "@/components/brand/sources-manager";
import { getBrand, listBrandSources } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoBrand } from "@/lib/demo-data";
import type { BrandSource } from "@/lib/types";

type PageProps = { params: { id: string } };

export default async function BrandSourcesPage({ params }: PageProps) {
  const demo = isDemoMode();

  let brand;
  let sources: BrandSource[] = [];
  let loadError = "";

  if (demo) {
    brand = demoBrand(params.id);
  } else {
    try {
      brand = await getBrand(params.id);
    } catch {
      notFound();
    }
    try {
      const data = await listBrandSources(params.id);
      sources = data.items;
    } catch (err) {
      loadError = err instanceof Error ? err.message : "Failed to load sources";
    }
  }

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}`}>{brand.name}</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Sources</span>
      </nav>

      {loadError ? (
        <div className="alert alert-danger">{loadError}</div>
      ) : (
        <SourcesManager brandId={brand.id} brandStatus={brand.status} initialSources={sources} />
      )}
    </div>
  );
}
