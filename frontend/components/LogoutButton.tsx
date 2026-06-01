"use client";

import { useAuth } from "@/context/AuthContext";

export function LogoutButton() {
  const { logout, user } = useAuth();
  if (!user) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
      <span className="meta" style={{ fontSize: "0.78rem" }}>{user.email}</span>
      <button
        onClick={() => void logout()}
        style={{ fontSize: "0.78rem", padding: "4px 10px" }}
      >
        Sign out
      </button>
    </div>
  );
}
