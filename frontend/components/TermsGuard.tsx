"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/context/AuthContext";

/**
 * Mounted in the root layout. When a signed-in user has not accepted the current
 * Terms & Conditions version, it shows a blocking modal that must be accepted
 * before continuing.
 */
export function TermsGuard() {
  const { user } = useAuth();
  const [required, setRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!user) {
      setRequired(false);
      return;
    }
    let cancelled = false;
    (async () => {
      const res = await fetch("/api/v1/auth/me").catch(() => null);
      if (!res || !res.ok) return;
      const data = (await res.json()) as { terms_acceptance_required?: boolean };
      if (!cancelled) setRequired(Boolean(data.terms_acceptance_required));
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function accept() {
    setSubmitting(true);
    try {
      const res = await fetch("/api/v1/auth/accept-terms", {
        method: "POST",
      });
      if (res.ok) setRequired(false);
    } finally {
      setSubmitting(false);
    }
  }

  if (!required) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div className="card stack" style={{ maxWidth: "440px" }}>
        <h3>Updated Terms &amp; Conditions</h3>
        <p className="meta">
          We&apos;ve updated our Terms &amp; Conditions. Please review and accept them to continue
          using 100xAI.
        </p>
        <a href="/terms" target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
          Read the Terms &amp; Conditions
        </a>
        <button type="button" onClick={accept} disabled={submitting}>
          {submitting ? "Accepting…" : "Accept & continue"}
        </button>
      </div>
    </div>
  );
}
