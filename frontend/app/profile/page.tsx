"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/context/AuthContext";
import { getSubscription } from "@/lib/api";
import type { BillingSubscriptionResponse } from "@/lib/types";

// Subscription states that mean the org currently has paid access.
const ACTIVE_STATES = ["active", "authenticated", "charged", "completed"];

type PaymentStatus = "active" | "inactive";

function paymentStatus(sub: BillingSubscriptionResponse | null): PaymentStatus {
  if (!sub) return "inactive";
  if (sub.plan_code && sub.plan_code !== "free") return "active";
  if (sub.subscription && ACTIVE_STATES.includes(sub.subscription.status)) return "active";
  return "inactive";
}

export default function ProfilePage() {
  const { user, org, loading } = useAuth();
  const [billing, setBilling] = useState<BillingSubscriptionResponse | null>(null);
  const [error, setError] = useState("");
  const [loadingBilling, setLoadingBilling] = useState(true);

  const refresh = useCallback(async () => {
    setLoadingBilling(true);
    try {
      setBilling(await getSubscription());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load payment status");
    } finally {
      setLoadingBilling(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const status = paymentStatus(billing);
  const isActive = status === "active";

  return (
    <div className="stack" style={{ padding: "24px", maxWidth: "720px", margin: "0 auto" }}>
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Profile</span>
      </nav>

      <div className="page-head" style={{ marginBottom: 8 }}>
        <div>
          <h1 className="page-title">Profile</h1>
          <p className="page-subtitle">Your account details and payment status.</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {/* Account */}
      <div className="card stack" style={{ padding: "24px" }}>
        <h3 style={{ marginBottom: 4 }}>Account</h3>
        <dl style={{ display: "grid", gridTemplateColumns: "140px 1fr", rowGap: 10, columnGap: 16, margin: 0 }}>
          <dt className="meta">Name</dt>
          <dd style={{ margin: 0 }}>{loading ? "…" : user?.name ?? "—"}</dd>
          <dt className="meta">Email</dt>
          <dd style={{ margin: 0 }}>{loading ? "…" : user?.email ?? "—"}</dd>
          <dt className="meta">Organization</dt>
          <dd style={{ margin: 0 }}>{loading ? "…" : org?.name ?? "—"}</dd>
        </dl>
      </div>

      {/* Payment status */}
      <div className="card stack" style={{ padding: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <h3 style={{ margin: 0 }}>Payment status</h3>
          <span className={`alert ${isActive ? "alert-success" : "alert-warning"}`} style={{ padding: "4px 12px", borderRadius: 100, fontSize: "0.8rem", fontWeight: 600 }}>
            {loadingBilling ? "Checking…" : isActive ? "Active" : "Not subscribed"}
          </span>
        </div>

        <dl style={{ display: "grid", gridTemplateColumns: "140px 1fr", rowGap: 10, columnGap: 16, margin: 0 }}>
          <dt className="meta">Current plan</dt>
          <dd style={{ margin: 0 }}>{billing?.plan_name ?? "Free"}</dd>
          {billing?.subscription && (
            <>
              <dt className="meta">Subscription</dt>
              <dd style={{ margin: 0 }}>{billing.subscription.status}</dd>
              {billing.subscription.current_period_end && (
                <>
                  <dt className="meta">Renews / ends</dt>
                  <dd style={{ margin: 0 }}>
                    {new Date(billing.subscription.current_period_end).toLocaleDateString()}
                  </dd>
                </>
              )}
            </>
          )}
        </dl>

        {!isActive && !loadingBilling && (
          <p className="meta" style={{ marginTop: 4 }}>
            A subscription is required to crawl websites and generate content.
          </p>
        )}

        <Link href="/billing" className="btn btn-red" style={{ alignSelf: "flex-start", marginTop: 4 }}>
          {isActive ? "Manage subscription" : "View plans & subscribe"}
        </Link>
      </div>
    </div>
  );
}
