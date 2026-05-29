import { notFound } from "next/navigation";

import { ManualProfileForm } from "@/components/brand/manual-profile-form";
import { getBrand } from "@/lib/api";

type PageProps = {
  params: { id: string };
};

export default async function BrandManualDnaPage({ params }: PageProps) {
  let brand;
  try {
    brand = await getBrand(params.id);
  } catch {
    notFound();
  }

  if (brand.dna_source !== "manual" || brand.status !== "DRAFT") {
    return (
      <section className="card stack">
        <h2 style={{ margin: 0 }}>Manual DNA form</h2>
        <p style={{ margin: 0 }}>
          Manual DNA submission is available only for manual-path brands in DRAFT status.
        </p>
      </section>
    );
  }

  return <ManualProfileForm brandId={brand.id} brandName={brand.name} />;
}
