import Link from "next/link";
import { CreateBrandForm } from "@/components/brand/create-brand-form";

export default function NewBrandPage() {
  return (
    <div className="stack">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>New Brand</span>
      </nav>
      <div className="page-head" style={{ marginBottom: 8 }}>
        <div>
          <h1 className="page-title">Create Brand</h1>
          <p className="page-subtitle">
            Onboard a new brand via automatic website crawl or manual profile entry.
          </p>
        </div>
      </div>
      <CreateBrandForm />
    </div>
  );
}
