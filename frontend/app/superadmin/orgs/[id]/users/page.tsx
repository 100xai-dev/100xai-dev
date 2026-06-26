"use client";

import { use, useCallback, useEffect, useState } from "react";

import {
  createOrgUser,
  deleteOrgUser,
  listOrgUsers,
  resetOrgUserPassword,
  updateOrgUser,
} from "@/lib/api";
import type { OrgUserOut } from "@/lib/types";

const ROLES = ["viewer", "team_member", "admin"];

export default function OrgUsersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: orgId } = use(params);
  const [users, setUsers] = useState<OrgUserOut[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("team_member");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await listOrgUsers(orgId);
      setUsers(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    }
  }, [orgId]);

  useEffect(() => { void load(); }, [load]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await createOrgUser(orgId, { name, email, role });
      setName(""); setEmail(""); setRole("team_member");
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add user");
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Users</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}

      <form onSubmit={add} style={{ display: "flex", gap: 8, margin: "16px 0", flexWrap: "wrap" }}>
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <button type="submit">Add user</button>
      </form>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
            <th>Email</th><th>Name</th><th>Role</th><th>Status</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} style={{ borderBottom: "1px solid #eee" }}>
              <td>{u.email}</td>
              <td>{u.name}</td>
              <td>
                <select
                  value={u.role}
                  onChange={async (e) => { await updateOrgUser(orgId, u.id, { role: e.target.value }); void load(); }}
                >
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </td>
              <td>{u.disabled ? "disabled" : "active"}</td>
              <td style={{ display: "flex", gap: 8 }}>
                <button onClick={async () => { await updateOrgUser(orgId, u.id, { disabled: !u.disabled }); void load(); }}>
                  {u.disabled ? "Enable" : "Disable"}
                </button>
                <button onClick={async () => { await resetOrgUserPassword(orgId, u.id); }}>Reset pwd</button>
                <button
                  style={{ color: "#b91c1c" }}
                  onClick={async () => {
                    if (window.confirm(`Delete ${u.email}?`)) { await deleteOrgUser(orgId, u.id); void load(); }
                  }}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
