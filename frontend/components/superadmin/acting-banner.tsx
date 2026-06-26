"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearActingOrg, getActingOrgId, getActingOrgName } from "@/lib/auth";

export function ActingBanner() {
  const router = useRouter();
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    if (getActingOrgId()) {
      setName(getActingOrgName() ?? "organization");
    }
  }, []);

  if (!name) return null;

  const exit = () => {
    clearActingOrg();
    setName(null);
    router.push("/superadmin");
    router.refresh();
  };

  return (
    <div
      style={{
        background: "#b91c1c",
        color: "white",
        padding: "8px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontSize: 14,
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      <span>
        Superadmin — acting as <b>{name}</b>
      </span>
      <button
        onClick={exit}
        style={{ background: "white", color: "#b91c1c", border: "none", borderRadius: 4, padding: "4px 12px", cursor: "pointer", fontWeight: 600 }}
      >
        Exit org
      </button>
    </div>
  );
}
