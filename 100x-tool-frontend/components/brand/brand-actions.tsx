"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { approveBrand, deleteBrand } from "@/lib/api";
import type { BrandSummary } from "@/lib/types";

export function BrandActions({ brand }: { brand: BrandSummary }) {
  const [pending, setPending] = useState<"" | "approve" | "delete">("");
  const [message, setMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const router = useRouter();

  const canApprove = brand.status === "PENDING_REVIEW";
  const canDelete = brand.status !== "PENDING_DELETE";

  async function onApprove() {
    try {
      setPending("approve");
      setMessage(null);
      const response = await approveBrand(brand.id);
      setMessage({ type: "success", text: `Brand approved and locked at ${new Date(response.locked_at).toLocaleString()}.` });
      router.refresh();
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Failed to approve brand" });
    } finally {
      setPending("");
    }
  }

  async function onDelete() {
    const confirmed = window.confirm(`Are you sure you want to permanently delete "${brand.name}"? This action cannot be undone.`);
    if (!confirmed) return;
    try {
      setPending("delete");
      setMessage(null);
      await deleteBrand(brand.id);
      setMessage({ type: "info", text: "Brand deleted." });
      router.push("/brands");
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Failed to request delete" });
    } finally {
      setPending("");
    }
  }

  return (
    <div className="card" style={{ padding: "22px 24px" }}>
      <h3 style={{ fontSize: "0.9375rem", marginBottom: 4 }}>Actions</h3>
      <p className="meta" style={{ marginBottom: 16 }}>Approve and lock the brand profile, or request a permanent deletion.</p>

      {message && (
        <div
          className={`alert alert-${message.type === "success" ? "success" : message.type === "error" ? "danger" : "info"}`}
          style={{ marginBottom: 16 }}
        >
          {message.text}
        </div>
      )}

      <div className="action-row">
        <button
          disabled={!canApprove || pending !== ""}
          onClick={onApprove}
          type="button"
        >
          {pending === "approve" ? "Approving…" : "Approve & Lock"}
        </button>
        <button
          className="btn-secondary danger"
          disabled={!canDelete || pending !== ""}
          onClick={onDelete}
          type="button"
          style={{ background: "transparent", color: "var(--danger)", borderColor: "var(--danger-border)" }}
        >
          {pending === "delete" ? "Requesting…" : "Delete Brand"}
        </button>
      </div>
    </div>
  );
}
