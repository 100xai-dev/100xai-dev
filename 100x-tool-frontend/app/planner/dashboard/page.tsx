"use client";

import Link from "next/link";

import { PF, useScheduler } from "@/lib/scheduler/context";
import { DOW, MONTHS, type PlatformKey } from "@/lib/scheduler/data";

export default function DashboardPage() {
  const { posts } = useScheduler();
  const total = posts.length;
  const scheduled = posts.filter((p) => p.status === "scheduled").length;
  const drafts = posts.filter((p) => p.status === "draft").length;
  const ai = posts.filter((p) => p.status === "ai").length;
  const upcoming = [...posts].sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time)).slice(0, 5);
  const byPf = (pf: PlatformKey) => posts.filter((p) => p.pf === pf).length;
  const max = Math.max(byPf("blog"), byPf("li"), byPf("ig"), 1);

  return (
    <>
      <div className="stat-grid">
        <div className="stat"><div className="sl">Total posts</div><div className="sv">{total}</div><div className="sd">↑ 12% vs last month</div></div>
        <div className="stat"><div className="sl">Scheduled</div><div className="sv" style={{ color: "var(--success)" }}>{scheduled}</div><div className="sd">ready to publish</div></div>
        <div className="stat"><div className="sl">Drafts</div><div className="sv" style={{ color: "var(--warning)" }}>{drafts}</div><div className="sd" style={{ color: "var(--warning)" }}>awaiting approval</div></div>
        <div className="stat"><div className="sl">AI-generated</div><div className="sv" style={{ color: "var(--info)" }}>{ai}</div><div className="sd" style={{ color: "var(--info)" }}>in review queue</div></div>
      </div>
      <div className="dash-grid">
        <div className="panel-box">
          <h3>Upcoming posts</h3>
          <div className="ph">Next 5 scheduled across all channels</div>
          {upcoming.map((p) => {
            const pf = PF[p.pf];
            const d = new Date(p.date + "T00:00");
            return (
              <div key={p.id} className="up-item">
                <div className="uic" style={{ background: pf.bg }}>{pf.ic}</div>
                <div className="ub">
                  <div className="t">{p.text}</div>
                  <div className="m">{DOW[(d.getDay() + 6) % 7]} {d.getDate()} {MONTHS[d.getMonth()].slice(0, 3)} · {p.time} · {pf.name}</div>
                </div>
              </div>
            );
          })}
        </div>
        <div className="panel-box">
          <h3>By channel</h3>
          <div className="ph">Distribution of your content mix</div>
          <div className="bar-row"><div className="bl">Blog</div><div className="bt"><span style={{ width: `${byPf("blog") / max * 100}%`, background: "var(--blog)" }} /></div><div className="bv">{byPf("blog")}</div></div>
          <div className="bar-row"><div className="bl">LinkedIn</div><div className="bt"><span style={{ width: `${byPf("li") / max * 100}%`, background: "var(--li)" }} /></div><div className="bv">{byPf("li")}</div></div>
          <div className="bar-row"><div className="bl">Instagram</div><div className="bt"><span style={{ width: `${byPf("ig") / max * 100}%`, background: "var(--ig)" }} /></div><div className="bv">{byPf("ig")}</div></div>
          <div style={{ marginTop: 24, paddingTop: 20, borderTop: "1px solid var(--border)" }}>
            <h3 style={{ fontSize: 16 }}>Approval queue</h3>
            <div className="ph" style={{ marginBottom: 12 }}>{drafts + ai} items pending review</div>
            <Link className="btn btn-red" style={{ width: "100%", justifyContent: "center" }} href="/planner">Open planner →</Link>
          </div>
        </div>
      </div>
    </>
  );
}
