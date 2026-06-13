"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { useAuth } from "@/context/AuthContext";

function VerifyEmailInner() {
  const params = useSearchParams();
  const token = params.get("token");
  const email = params.get("email") ?? "";
  const { verifyEmail, resendVerification } = useAuth();

  const [status, setStatus] = useState<"idle" | "verifying" | "error">(token ? "verifying" : "idle");
  const [error, setError] = useState("");
  const [resent, setResent] = useState(false);
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;
    verifyEmail(token).catch((err) => {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Verification failed");
    });
  }, [token, verifyEmail]);

  async function handleResend() {
    if (!email) return;
    await resendVerification(email);
    setResent(true);
  }

  return (
    <div className="auth-shell">
      <div className="auth-card card stack">
        <div>
          <div className="meta" style={{ color: "var(--accent)", letterSpacing: "0.15em" }}>
            100xAI // BRAND_OS
          </div>
          <h2 style={{ marginTop: "8px" }}>Verify your email</h2>
        </div>

        {status === "verifying" && <p className="meta">Verifying your email…</p>}

        {status === "error" && (
          <>
            <p className="text-danger" role="alert">
              {error}
            </p>
            <p className="meta">The link may have expired. Request a new one below.</p>
          </>
        )}

        {status === "idle" && (
          <p className="meta">
            We&apos;ve sent a verification link{email ? ` to ${email}` : ""}. Open it to activate your
            account. Didn&apos;t get it? Check spam or resend below.
          </p>
        )}

        {(status === "idle" || status === "error") && (
          <>
            {email && (
              <button type="button" onClick={handleResend} disabled={resent}>
                {resent ? "Verification email sent" : "Resend verification email"}
              </button>
            )}
            <p className="meta" style={{ textAlign: "center" }}>
              <Link href="/login" style={{ color: "var(--accent)" }}>
                Back to sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="auth-shell" />}>
      <VerifyEmailInner />
    </Suspense>
  );
}
