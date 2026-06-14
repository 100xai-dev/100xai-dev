import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/LogoutButton";

// Brand-admin shell. Editorial theme — warm background + centered column.
// Kept intentionally light so it composes with the existing globals.css theme.
export default function BrandsLayout({ children }: { children: ReactNode }) {
  return (
    <div style={{ minHeight: "100vh" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "18px 32px",
          borderBottom: "1px solid var(--border-soft)",
          maxWidth: 1100,
          margin: "0 auto",
        }}
      >
        <Link href="/brands" className="brand">
          <span className="dot" />100x<b>AI</b>
        </Link>
        <nav className="nav-links">
          <Link href="/brands">Brands</Link>
          <LogoutButton />
        </nav>
      </header>
      <main className="admin-shell">{children}</main>
    </div>
  );
}
