import Link from "next/link";
import { notFound } from "next/navigation";

import { ContentCalendar } from "@/components/brand/content-calendar";
import { getBrand, getBrandCalendar } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoBrand } from "@/lib/demo-data";
import type { CalendarEntry } from "@/lib/types";

type PageProps = { params: { id: string } };

export default async function BrandSchedulePage({ params }: PageProps) {
  const demo = isDemoMode();
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;

  let brand;
  let entries: CalendarEntry[] = [];
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
      entries = await getBrandCalendar(params.id, year, month);
    } catch (err) {
      loadError = err instanceof Error ? err.message : "Failed to load calendar";
    }
  }

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}`}>{brand.name}</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Content Calendar</span>
      </nav>

      <div>
        <h1 className="page-title">Content Calendar</h1>
        <p className="page-subtitle">Schedule keyword-driven blog posts and auto-publish them to WordPress.</p>
      </div>

      {loadError ? (
        <div className="alert alert-danger">{loadError}</div>
      ) : (
        <ContentCalendar
          brandId={brand.id}
          brandStatus={brand.status}
          initialYear={year}
          initialMonth={month}
          initialEntries={entries}
        />
      )}
    </div>
  );
}
