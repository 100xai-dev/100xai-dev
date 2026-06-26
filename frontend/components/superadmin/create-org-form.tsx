"use client";

import { useState } from "react";

import { createOrganization } from "@/lib/api";

export function CreateOrgForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [orgName, setOrgName] = useState("");
  const [plan, setPlan] = useState("free");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!open) {
    return <button onClick={() => setOpen(true)}>+ Create organization</button>;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createOrganization({
        organization_name: orgName,
        plan_code: plan,
        admin_name: adminName,
        admin_email: adminEmail,
      });
      setOpen(false);
      setOrgName(""); setAdminName(""); setAdminEmail(""); setPlan("free");
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create organization");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} style={{ display: "grid", gap: 8, maxWidth: 360, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
      <h3>Create organization</h3>
      <input placeholder="Organization name" value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
      <select value={plan} onChange={(e) => setPlan(e.target.value)}>
        <option value="free">free</option>
        <option value="starter">starter</option>
        <option value="pro">pro</option>
      </select>
      <input placeholder="Admin name" value={adminName} onChange={(e) => setAdminName(e.target.value)} required />
      <input type="email" placeholder="Admin email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} required />
      {error && <p style={{ color: "red" }}>{error}</p>}
      <div style={{ display: "flex", gap: 8 }}>
        <button type="submit" disabled={busy}>{busy ? "Creating…" : "Create"}</button>
        <button type="button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}
