"use client";

import { useState } from "react";

import { useAuth } from "@/context/AuthContext";

// Styled to blend in with `.nav-links a` (see globals.css) since it sits in the
// editorial header nav alongside the anchor links.
export function LogoutButton() {
  const { logout } = useAuth();
  const [busy, setBusy] = useState(false);

  const onClick = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await logout();
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      style={{
        background: "none",
        border: "none",
        padding: 0,
        color: "var(--ink-soft)",
        fontSize: "13.5px",
        fontWeight: 500,
        letterSpacing: ".02em",
        cursor: busy ? "default" : "pointer",
        fontFamily: "inherit",
        transition: ".2s",
      }}
    >
      {busy ? "Signing out…" : "Logout"}
    </button>
  );
}
