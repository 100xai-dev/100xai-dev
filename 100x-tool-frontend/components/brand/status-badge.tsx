import type { BrandStatus } from "@/lib/types";

const statusConfig: Record<BrandStatus, { label: string; color: string; bg: string; border: string }> = {
  DRAFT:          { label: "Draft",          color: "#6b7280", bg: "#f3f4f6", border: "#e5e7eb" },
  CRAWLING:       { label: "Crawling",       color: "#0284c7", bg: "#e0f2fe", border: "#7dd3fc" },
  EXTRACTING:     { label: "Extracting",     color: "#7c3aed", bg: "#ede9fe", border: "#c4b5fd" },
  INGESTING:      { label: "Ingesting",      color: "#0891b2", bg: "#cffafe", border: "#67e8f9" },
  PENDING_REVIEW: { label: "Pending Review", color: "#d97706", bg: "#fef3c7", border: "#fcd34d" },
  READY:          { label: "Ready",          color: "#059669", bg: "#d1fae5", border: "#6ee7b7" },
  FAILED:         { label: "Failed",         color: "#dc2626", bg: "#fee2e2", border: "#fca5a5" },
  PENDING_DELETE: { label: "Pending Delete", color: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
};

export function StatusBadge({ status }: { status: BrandStatus }) {
  const cfg = statusConfig[status] ?? statusConfig.DRAFT;
  return (
    <span
      className="status-badge"
      style={{ color: cfg.color, background: cfg.bg, borderColor: cfg.border }}
    >
      {cfg.label}
    </span>
  );
}
