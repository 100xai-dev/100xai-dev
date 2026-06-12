"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { setupWordPress, testWordPress } from "@/lib/api";

type TestState =
  | { kind: "idle" }
  | { kind: "ok"; info: string }
  | { kind: "err"; msg: string };

export function WordPressSetupForm({
  brandId,
  initialSiteUrl = "",
  initialUsername = "",
  currentStatus,
}: {
  brandId: string;
  initialSiteUrl?: string;
  initialUsername?: string;
  currentStatus?: string | null;
}) {
  const router = useRouter();
  const [siteUrl, setSiteUrl] = useState(initialSiteUrl);
  const [username, setUsername] = useState(initialUsername);
  const [password, setPassword] = useState("");
  const [defaultStatus, setDefaultStatus] = useState("draft");

  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [test, setTest] = useState<TestState>({ kind: "idle" });
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  function validate(): string {
    if (!siteUrl.trim()) return "Site URL is required.";
    if (!username.trim()) return "Username is required.";
    if (!password.trim()) return "Application password is required.";
    return "";
  }

  async function onTest() {
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setError("");
    setSaved("");
    setTesting(true);
    setTest({ kind: "idle" });
    try {
      const res = await testWordPress(brandId, {
        site_url: siteUrl.trim(),
        username: username.trim(),
        password: password,
        auto_publish: defaultStatus === "publish",
      });
      if (res.success) {
        const name = (res.site_info?.name as string) || "WordPress site";
        const version = (res.site_info?.wp_version as string) || "";
        setTest({ kind: "ok", info: version ? `${name} · WP ${version}` : name });
      } else {
        setTest({ kind: "err", msg: res.error || "Connection test failed" });
      }
    } catch (err) {
      setTest({ kind: "err", msg: err instanceof Error ? err.message : "Connection test failed" });
    } finally {
      setTesting(false);
    }
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setError("");
    setSaved("");
    setSaving(true);
    try {
      const res = await setupWordPress(brandId, {
        site_url: siteUrl.trim(),
        username: username.trim(),
        application_password: password,
        default_status: defaultStatus,
        default_categories: [],
        default_author_id: null,
      });
      const name = (res.site_info?.name as string) || "WordPress";
      setSaved(`Connected to ${name}. Status: ${res.status}.`);
      setPassword("");
      router.refresh();
    } catch (err) {
      // Backend returns 422 with the connection error when the test fails.
      setError(err instanceof Error ? err.message : "Failed to save WordPress configuration");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card stack" onSubmit={onSave} style={{ maxWidth: 600 }}>
      {currentStatus && (
        <div
          className="status-badge"
          style={
            currentStatus === "active"
              ? { color: "var(--success)", background: "var(--success-light)", borderColor: "var(--success-border)", alignSelf: "flex-start" }
              : { color: "var(--warning)", background: "var(--warning-light)", borderColor: "var(--warning-border)", alignSelf: "flex-start" }
          }
        >
          {currentStatus === "active" ? "Connected" : `Status: ${currentStatus}`}
        </div>
      )}

      <label>
        WordPress Site URL
        <input
          value={siteUrl}
          onChange={(e) => setSiteUrl(e.target.value)}
          placeholder="https://yourblog.com"
          style={{ marginTop: 6 }}
        />
      </label>

      <label>
        Username
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="admin"
          autoComplete="username"
          style={{ marginTop: 6 }}
        />
      </label>

      <label>
        Application Password
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          placeholder="xxxx xxxx xxxx xxxx"
          autoComplete="new-password"
          style={{ marginTop: 6 }}
        />
        <span className="meta" style={{ marginTop: 4, display: "block" }}>
          Create one under WordPress → Users → Profile → Application Passwords.
        </span>
      </label>

      <label>
        Default Post Status
        <select value={defaultStatus} onChange={(e) => setDefaultStatus(e.target.value)} style={{ marginTop: 6 }}>
          <option value="draft">Draft</option>
          <option value="pending">Pending</option>
          <option value="publish">Publish</option>
        </select>
      </label>

      {test.kind === "ok" && <div className="alert alert-success">✓ {test.info}</div>}
      {test.kind === "err" && <div className="alert alert-danger">✗ {test.msg}</div>}
      {error && <div className="alert alert-danger">{error}</div>}
      {saved && <div className="alert alert-success">{saved}</div>}

      <div className="action-row" style={{ paddingTop: 4 }}>
        <button type="button" className="btn-secondary" onClick={onTest} disabled={testing || saving}>
          {testing ? "Testing…" : "Test Connection"}
        </button>
        <button type="submit" disabled={saving || testing}>
          {saving ? "Saving…" : "Save Configuration"}
        </button>
      </div>
    </form>
  );
}
