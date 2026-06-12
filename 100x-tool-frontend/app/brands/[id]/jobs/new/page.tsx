import Link from "next/link";
import { notFound } from "next/navigation";

import { TriggerJobForm } from "@/components/brand/trigger-job-form";
import { getBrand } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoBrand } from "@/lib/demo-data";

type PageProps = { params: { id: string } };

export default async function NewJobPage({ params }: PageProps) {
  let brand;
  if (isDemoMode()) {
    brand = demoBrand(params.id);
  } else {
    try {
      brand = await getBrand(params.id);
    } catch {
      notFound();
    }
  }

  return (
    <div className="stack stack-lg">
      {/* Breadcrumb */}
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}`}>{brand.name}</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}/jobs`}>Jobs</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>New Run</span>
      </nav>

      {brand.status !== "READY" ? (
        <div className="alert alert-warning">
          <span>⚠</span>
          <span>
            This brand must be in READY status before running the pipeline. Current status:{" "}
            {brand.status}.
          </span>
        </div>
      ) : (
        <TriggerJobForm brandId={brand.id} brandName={brand.name} />
      )}
    </div>
  );
}
