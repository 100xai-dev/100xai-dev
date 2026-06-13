"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import ComposeModal from "@/components/scheduler/compose-modal";
import Toast from "@/components/scheduler/toast";
import { MONTHS, startOfWeek, type PlatformKey } from "@/lib/scheduler/data";
import { PF, useScheduler } from "@/lib/scheduler/context";

const PAGE_TITLES: Record<string, string> = {
  "/planner": "Content Planner",
  "/planner/dashboard": "Dashboard",
  "/planner/ai": "AI Studio",
  "/planner/queue": "Auto-Queue",
  "/planner/analytics": "Analytics",
  "/planner/settings": "Settings",
};

// Routes whose content area gets the standard 28px padding (calendar + ai studio manage their own).
const PAD_ROUTES = new Set(["/planner/dashboard", "/planner/queue", "/planner/analytics", "/planner/settings"]);

const CHANNELS: { pf: PlatformKey; label: string }[] = [
  { pf: "blog", label: "Blog" },
  { pf: "li", label: "LinkedIn" },
  { pf: "ig", label: "Instagram" },
];

function dateLabel(view: string, anchor: Date): string {
  if (view === "month") return `${MONTHS[anchor.getMonth()]} ${anchor.getFullYear()}`;
  if (view === "list") return "Upcoming";
  const ws = startOfWeek(anchor);
  const we = new Date(ws);
  we.setDate(we.getDate() + 6);
  return `${ws.getDate()} ${MONTHS[ws.getMonth()].slice(0, 3)} – ${we.getDate()} ${MONTHS[we.getMonth()].slice(0, 3)}`;
}

export default function PlannerLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const {
    brand, view, setView, viewAnchor, shiftDate, goToday,
    filters, toggleFilter, search, setSearch, visiblePosts, openCompose,
  } = useScheduler();

  const isPlanner = pathname === "/planner";
  const title = PAGE_TITLES[pathname] ?? "Content Planner";
  const padded = PAD_ROUTES.has(pathname);
  const av = (brand.name.trim()[0] || "R").toUpperCase();

  const navItem = (href: string, label: string, soon?: boolean) => (
    <Link href={href} className={`nav-item${pathname === href ? " active" : ""}`}>
      {label}{soon && <span className="soon">SOON</span>}
    </Link>
  );

  return (
    <div className="planner-app">
      <aside className="sidebar">
        <div className="brand"><span className="dot" />Schedu<b>lr</b></div>

        <div className="nav-group">
          {navItem("/planner", "Planner")}
          {navItem("/planner/dashboard", "Dashboard")}
          <div className="nav-item" onClick={openCompose}>Composer</div>
        </div>

        <div className="nav-group">
          <div className="gl">Automation</div>
          {navItem("/planner/ai", "AI Studio", true)}
          {navItem("/planner/queue", "Auto-Queue", true)}
          {navItem("/planner/analytics", "Analytics", true)}
        </div>

        <div className="nav-group">
          <div className="gl">Workspace</div>
          {navItem("/planner/settings", "Settings")}
        </div>

        <div className="sidebar-foot">
          <div className="connected">
            <div className="c" style={{ background: "var(--blog)" }} title="Blog connected">B</div>
            <div className="c" style={{ background: "var(--li)" }} title="LinkedIn connected">in</div>
            <div className="c" style={{ background: "var(--ig)" }} title="Instagram connected">ig</div>
          </div>
          <div className="acct">
            <div className="av">{av}</div>
            <div>
              <div className="nm">Rajeev · 100xAI</div>
              <div className="em">rajeev@100xai.co</div>
            </div>
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <h2>{title}</h2>
          {isPlanner && (
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <div className="view-toggle">
                {(["week", "month", "list"] as const).map((v) => (
                  <button key={v} className={view === v ? "active" : ""} onClick={() => setView(v)}>
                    {v[0].toUpperCase() + v.slice(1)}
                  </button>
                ))}
              </div>
              <div className="date-nav">
                <button onClick={() => shiftDate(-1)}>‹</button>
                <button className="today" onClick={goToday}>Today</button>
                <button onClick={() => shiftDate(1)}>›</button>
              </div>
              <div className="date-label">{dateLabel(view, viewAnchor)}</div>
            </div>
          )}
          <div className="spacer" />
          {isPlanner && (
            <div className="search">
              <input type="text" placeholder="Search posts…" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
          )}
          <button className="btn btn-red" onClick={openCompose}>＋ New Post</button>
        </div>

        {isPlanner && (
          <div className="filter-bar">
            <span className="fl">Channels</span>
            {CHANNELS.map(({ pf, label }) => (
              <div
                key={pf}
                className={`chip ${filters[pf] ? "on" : "off"}`}
                onClick={() => toggleFilter(pf)}
              >
                <span className="ci" style={{ background: PF[pf].bg }}>{PF[pf].ic}</span> {label}
              </div>
            ))}
            <div className="spacer" />
            <span className="fl">{visiblePosts().length} POSTS</span>
          </div>
        )}

        <div className={`content${padded ? " pad" : ""}`}>{children}</div>
      </main>

      <ComposeModal />
      <Toast />
    </div>
  );
}
