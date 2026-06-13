"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      // login() posts to /v1/auth/login, stores the session/cookie, and
      // routes to /brands on success (or /verify-email if unverified).
      await login(email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-art">
        <div className="glow" />
        <div className="grid-bg" />
        <div className="brand"><span className="dot" />Schedu<b>lr</b></div>
        <div className="art-quote">
          <h2>Your content<br />pipeline, on <span className="accent">autopilot.</span></h2>
          <p>Sign in to plan, draft and publish across every channel from a single calendar.</p>
          <div className="mini-cal">
            <div className="mc"><div className="d">MON</div><div className="bar" style={{ background: "var(--blog)" }} /></div>
            <div className="mc"><div className="d">TUE</div><div className="bar" style={{ background: "var(--li)" }} /></div>
            <div className="mc"><div className="d">WED</div><div className="bar" style={{ background: "var(--ig)" }} /></div>
            <div className="mc"><div className="d">THU</div><div className="bar" style={{ background: "var(--li)" }} /></div>
            <div className="mc"><div className="d">FRI</div><div className="bar" style={{ background: "var(--blog)" }} /></div>
          </div>
        </div>
      </div>
      <div className="login-form-wrap">
        <Link className="back-home" href="/">← Back to site</Link>
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="brand"><span className="dot" />Schedu<b>lr</b></div>
          <h3>Welcome back</h3>
          <p className="sub">Sign in to your 100xAI workspace.</p>
          <div className="field">
            <label htmlFor="email">Work email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@100xai.co"
              autoComplete="email"
              required
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </div>
          {error && (
            <p className="login-error" role="alert" style={{ color: "var(--accent)", fontSize: 13, margin: "0 0 4px" }}>
              {error}
            </p>
          )}
          <button className="btn btn-red" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in →"}
          </button>
          <div className="login-alt">No account yet? <Link href="/signup">Request access</Link></div>
        </form>
      </div>
    </div>
  );
}
