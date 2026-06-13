"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/context/AuthContext";

export default function SignupPage() {
  const { signup } = useAuth();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    organizationName: "",
  });
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!form.name || !form.email || !form.password || !form.organizationName) {
      setError("All fields are required.");
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (!acceptedTerms) {
      setError("You must accept the Terms & Conditions to continue.");
      return;
    }

    setLoading(true);
    try {
      await signup(form.name, form.email, form.password, form.organizationName);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card card stack">
        <div>
          <div className="meta" style={{ color: "var(--accent)", letterSpacing: "0.15em" }}>
            100xAI // BRAND_OS
          </div>
          <h2 style={{ marginTop: "8px" }}>Create account</h2>
        </div>

        <form className="stack" onSubmit={handleSubmit}>
          <label>
            Full name
            <input
              type="text"
              autoComplete="name"
              value={form.name}
              onChange={set("name")}
              required
            />
          </label>

          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={set("email")}
              required
            />
          </label>

          <label>
            Organization name
            <input
              type="text"
              autoComplete="organization"
              value={form.organizationName}
              onChange={set("organizationName")}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={set("password")}
              required
            />
            <span className="meta" style={{ fontSize: "0.75rem", marginTop: "4px" }}>
              Min 8 chars, uppercase, lowercase, number, special character
            </span>
          </label>

          <label>
            Confirm password
            <input
              type="password"
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={set("confirmPassword")}
              required
            />
          </label>

          <label style={{ display: "flex", flexDirection: "row", alignItems: "flex-start", gap: "8px" }}>
            <input
              type="checkbox"
              checked={acceptedTerms}
              onChange={(e) => setAcceptedTerms(e.target.checked)}
              style={{ width: "auto", marginTop: "4px" }}
            />
            <span className="meta" style={{ fontSize: "0.8rem" }}>
              I agree to the{" "}
              <Link href="/terms" target="_blank" style={{ color: "var(--accent)" }}>
                Terms &amp; Conditions
              </Link>
              .
            </span>
          </label>

          {error && (
            <p className="text-danger" role="alert" aria-live="assertive">
              {error}
            </p>
          )}

          <button type="submit" disabled={loading || !acceptedTerms}>
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="meta" style={{ textAlign: "center" }}>
          Already have an account?{" "}
          <Link href="/login" style={{ color: "var(--accent)" }}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
