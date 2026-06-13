"use client";

import { useCallback, useEffect, useState } from "react";

import { cancelSubscription, getSubscription, listPlans, subscribeToPlan } from "@/lib/api";
import type { BillingSubscriptionResponse, PlanOut } from "@/lib/types";

type RazorpayOptions = {
  key: string;
  subscription_id: string;
  name: string;
  description: string;
  handler: (response: unknown) => void;
  theme?: { color?: string };
};

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => { open: () => void };
  }
}

const CHECKOUT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

function loadCheckout(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = CHECKOUT_SRC;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanOut[]>([]);
  const [current, setCurrent] = useState<BillingSubscriptionResponse | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [{ plans }, sub] = await Promise.all([listPlans(), getSubscription()]);
      setPlans(plans);
      setCurrent(sub);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load billing");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleSubscribe(planCode: string) {
    setError("");
    setBusy(planCode);
    try {
      const ok = await loadCheckout();
      if (!ok || !window.Razorpay) throw new Error("Could not load Razorpay Checkout");
      const { subscription_id, key_id } = await subscribeToPlan(planCode);
      const rzp = new window.Razorpay({
        key: key_id,
        subscription_id,
        name: "100xAI",
        description: `Subscribe to ${planCode}`,
        theme: { color: "#6c5ce7" },
        handler: () => {
          // Activation is confirmed via webhook; poll our backend for the new status.
          setTimeout(refresh, 2000);
        },
      });
      rzp.open();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Subscription failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleCancel() {
    setBusy("cancel");
    try {
      await cancelSubscription();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    } finally {
      setBusy(null);
    }
  }

  const activePlan = current?.plan_code ?? "free";

  return (
    <div className="stack" style={{ padding: "24px", maxWidth: "960px", margin: "0 auto" }}>
      <div>
        <h2>Billing &amp; plans</h2>
        <p className="meta">
          Current plan: <strong>{current?.plan_name ?? "Free"}</strong>
          {current?.subscription && ` · subscription ${current.subscription.status}`}
        </p>
      </div>

      {error && (
        <p className="text-danger" role="alert">
          {error}
        </p>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
        }}
      >
        {plans.map((plan) => {
          const isCurrent = plan.code === activePlan;
          return (
            <div key={plan.code} className="card stack">
              <h3>{plan.name}</h3>
              <p style={{ fontSize: "1.4rem", fontWeight: 600 }}>
                ₹{plan.price_inr}
                <span className="meta" style={{ fontSize: "0.8rem" }}>
                  {" "}
                  / month
                </span>
              </p>
              <ul className="meta" style={{ paddingLeft: "18px" }}>
                {Object.entries(plan.limits).map(([resource, limit]) => (
                  <li key={resource}>
                    {limit < 0 ? "Unlimited" : limit} {resource}
                  </li>
                ))}
              </ul>
              {isCurrent ? (
                <button type="button" disabled>
                  Current plan
                </button>
              ) : plan.subscribable ? (
                <button
                  type="button"
                  onClick={() => handleSubscribe(plan.code)}
                  disabled={busy !== null}
                >
                  {busy === plan.code ? "Starting…" : `Subscribe to ${plan.name}`}
                </button>
              ) : (
                <button type="button" disabled title="Plan not configured for purchase">
                  Unavailable
                </button>
              )}
            </div>
          );
        })}
      </div>

      {current?.subscription && current.subscription.status !== "cancelled" && (
        <button
          type="button"
          className="topbar-link"
          onClick={handleCancel}
          disabled={busy === "cancel"}
          style={{ alignSelf: "flex-start" }}
        >
          {busy === "cancel" ? "Cancelling…" : "Cancel subscription"}
        </button>
      )}
    </div>
  );
}
