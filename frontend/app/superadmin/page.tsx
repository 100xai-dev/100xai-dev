"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CreateOrgForm } from "@/components/superadmin/create-org-form";
import {
  deleteOrganization,
  enterOrganization,
  listOrganizations,
  suspendOrganization,
  unsuspendOrganization,
} from "@/lib/api";
import { setActingOrg } from "@/lib/auth";
import type { OrgListItem } from "@/lib/types";

export default function SuperadminPage() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<OrgListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await listOrganizations();
      setOrgs(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load organizations");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const enter = async (org: OrgListItem) => {
    await enterOrganization(org.id);
    setActingOrg(org.id, org.name);
    router.push("/brands");
    router.refresh();
  };

  const toggleSuspend = async (org: OrgListItem) => {
    if (org.status === "suspended") await unsuspendOrganization(org.id);
    else await suspendOrganization(org.id);
    void load();
  };

  const remove = async (org: OrgListItem) => {
    const typed = window.prompt(`Type the org name to permanently delete it:\n${org.name}`);
    if (typed !== org.name) return;
    await deleteOrganization(org.id);
    void load();
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Organizations</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <div style={{ margin: "16px 0" }}>
        <CreateOrgForm onCreated={load} />
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
            <th>Name</th><th>Plan</th><th>Status</th><th>Users</th><th>Brands</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {orgs.map((o) => (
            <tr key={o.id} style={{ borderBottom: "1px solid #eee" }}>
              <td>{o.name}</td>
              <td>{o.plan_code}</td>
              <td>{o.status}</td>
              <td>{o.user_count}</td>
              <td>{o.brand_count}</td>
              <td style={{ display: "flex", gap: 8 }}>
                <button onClick={() => enter(o)}>Enter</button>
                <button onClick={() => router.push(`/superadmin/orgs/${o.id}/users`)}>Users</button>
                <button onClick={() => toggleSuspend(o)}>{o.status === "suspended" ? "Unsuspend" : "Suspend"}</button>
                <button onClick={() => remove(o)} style={{ color: "#b91c1c" }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
