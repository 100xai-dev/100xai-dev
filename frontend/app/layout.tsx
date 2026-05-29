import type { Metadata } from "next";
import { DM_Sans, DM_Mono } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const sans = DM_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const mono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "100xAI — Brand OS",
  description: "Internal onboarding and brand management platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html className={`${sans.variable} ${mono.variable}`} lang="en">
      <body>
        <div className="app-shell">
          <header className="topbar">
            <div className="topbar-brand">
              <div className="topbar-logo-mark">AI</div>
              <div>
                <div className="topbar-title">100xAI</div>
                <div className="topbar-status-pulse">
                  <span className="pulse-dot" />
                  <span className="topbar-kicker">Live · Brand OS</span>
                </div>
              </div>
            </div>
            <nav className="topbar-nav">
              <Link className="topbar-link" href="/brands">
                Dashboard
              </Link>
              <Link className="topbar-link primary" href="/brands/new">
                + New Brand
              </Link>
            </nav>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
