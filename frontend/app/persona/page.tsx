"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { useScheduler } from "@/lib/scheduler/context";
import { buildPersona } from "@/lib/scheduler/persona";

export default function PersonaPage() {
  const router = useRouter();
  const { brand } = useScheduler();
  const p = buildPersona(brand);
  const rootRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            obs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -50px 0px" },
    );
    root.querySelectorAll(".pz-reveal").forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  const goPlanner = () => router.push("/planner");
  const goEdit = () => router.push("/onboarding");

  return (
    <section
      id="persona"
      ref={rootRef}
      style={{ "--bz": p.accent, "--bz2": p.accent2, "--bz-tint": p.tint } as React.CSSProperties}
    >
      <div className="pz-topbar"><div className="pz-topbar-inner">
        <div className="pz-prep">Prepared by <em>100XAI</em> · for {p.d.name}</div>
        <div className="pz-tb-actions">
          <button className="pz-tb-btn" onClick={goEdit}>Edit answers</button>
          <button className="pz-tb-btn" onClick={goPlanner}>Skip to planner →</button>
        </div>
      </div></div>

      <div className="pz-hero"><div className="pz-hero-inner">
        <div className="pz-hero-left">
          <div className="pz-pill">Brand Persona · Vol. I</div>
          <h1 className="pz-hero-title">
            <span className="ln"><span>
              {p.titleWords.lead && <>{p.titleWords.lead} </>}
              <span className="it">{p.titleWords.last}</span>
            </span></span>
          </h1>
          <p className="pz-hero-sub">{p.d.one} — for <em>{p.d.aud}</em>.</p>
          <div className="pz-coord">
            <div><span className="lab">Website</span><span className="val">{p.d.url}</span></div>
            <div><span className="lab">Voice</span><span className="val">{p.voiceLabel}</span></div>
            <div><span className="lab">Prepared by</span><span className="val">100XAI</span></div>
            <div><span className="lab">Edition</span><span className="val">01 · {p.year}</span></div>
          </div>
        </div>
        <div className="pz-hero-art">
          <svg viewBox="-100 -100 200 200">
            <circle className="pz-ring r1" r="90" /><circle className="pz-ring r2" r="90" /><circle className="pz-ring r3" r="90" />
            <g className="pz-orbit">
              <line className="pz-spoke" x1="0" y1="0" x2="0" y2="-72" /><line className="pz-spoke" x1="0" y1="0" x2="68" y2="24" />
              <line className="pz-spoke" x1="0" y1="0" x2="-42" y2="58" /><line className="pz-spoke" x1="0" y1="0" x2="42" y2="58" />
              <line className="pz-spoke" x1="0" y1="0" x2="-68" y2="24" />
              <circle className="pz-node b" cx="0" cy="-72" r="5" /><circle className="pz-node" cx="68" cy="24" r="4" />
              <circle className="pz-node" cx="-42" cy="58" r="4" /><circle className="pz-node b" cx="42" cy="58" r="4" />
              <circle className="pz-node" cx="-68" cy="24" r="4" />
            </g>
            <circle className="pz-hub" cx="0" cy="0" r="26" />
            <text className="pz-hub-t" x="0" y="5" textAnchor="middle">{p.initial}</text>
          </svg>
        </div>
      </div></div>

      <div className="pz-essence pz-reveal">
        <p>{p.d.name} is <em>{p.d.one}</em>. The promise is simple: show up <em>{p.toneAdj}</em>, and never break the trust we ask for.</p>
      </div>

      <section className="pz-sec">
        <div className="pz-reveal"><div className="pz-sec-num">01 · Palette</div><h2 className="pz-sec-title">A palette built from <em>the brand</em></h2></div>
        <div className="pz-palette">
          {p.palette.map((s) => (
            <div key={s.n} className="pz-sw pz-reveal">
              <div className="chip" style={{ background: s.c }} />
              <div className="meta"><div className="nm">{s.n}</div><div className="hx">{s.hx.toUpperCase()}</div></div>
            </div>
          ))}
        </div>
      </section>

      <section className="pz-sec wide"><div className="pz-sec-inner" style={{ maxWidth: 1180, margin: "0 auto" }}>
        <div className="pz-reveal"><div className="pz-sec-num">02 · Voice</div><h2 className="pz-sec-title">How {p.d.name} <em>sounds</em></h2></div>
        <div className="pz-voice">
          {p.voiceCards.map((v) => (
            <div key={v.vn} className="pz-vcard pz-reveal"><span className="vn">{v.vn}</span><div><h5>{v.h}</h5><p>{v.p}</p></div></div>
          ))}
        </div>
      </div></section>

      <section className="pz-sec">
        <div className="pz-reveal"><div className="pz-sec-num">03 · What We Believe</div><h2 className="pz-sec-title">A few <em>non-negotiable</em> convictions</h2></div>
        <div className="pz-cards">
          {p.believe.map((c) => (
            <div key={c.ix} className="pz-card pz-reveal"><span className="ix">{c.ix}</span><h5>{c.h}</h5><p>{c.p}</p></div>
          ))}
        </div>
      </section>

      <section className="pz-sec">
        <div className="pz-reveal"><div className="pz-sec-num">04 · Founder</div><h2 className="pz-sec-title">The person <em>behind</em> the mission</h2></div>
        <div className="pz-founder">
          <div className="pz-portrait pz-reveal">
            <span className="mono-init">{p.initial}</span>
            <div className="stamp"><span className="who">{p.d.founder}</span><span className="role">{p.d.role}</span></div>
          </div>
          <div className="pz-founder-body pz-reveal">
            <div className="pz-quote">“We didn’t set out to build a company. We set out to fix something that kept us up at night — and {p.d.name} is what that looks like in the world.”
              <span className="src">{p.d.founder} · {p.d.role}</span></div>
            <p>{p.d.founder} leads {p.d.name} with one fixed point on the horizon: <strong>{p.d.mission}</strong>. Every decision is weighed against it.</p>
            <p>The work is for <em>{p.d.aud}</em> — and the voice never forgets who it’s really talking to.</p>
          </div>
        </div>
      </section>

      <section className="pz-sec">
        <div className="pz-reveal"><div className="pz-sec-num">05 · Values</div><h2 className="pz-sec-title">The <em>six</em> commitments</h2></div>
        <div className="pz-cards">
          {p.values.map((c) => (
            <div key={c.ix} className="pz-card pz-reveal"><span className="ix">{c.ix}</span><h5>{c.h}</h5><p>{c.p}</p></div>
          ))}
        </div>
      </section>

      <section className="pz-sec dark"><div className="pz-sec-inner">
        <div className="pz-reveal"><div className="pz-sec-num">06 · Goal</div><h2 className="pz-sec-title" style={{ color: "#fff" }}>What we are <em>building toward</em></h2></div>
        <div className="pz-goal-lead pz-reveal">{p.d.name} is building toward <em>{p.d.mission}</em>.</div>
      </div></section>

      <footer className="pz-footer"><div className="pz-footer-inner">
        <div className="pz-footer-grid">
          <div><h6>A note from 100XAI</h6><p className="pz-footer-lead">This persona was composed by <em>100XAI</em> for {p.d.name} — a living reference for everyone building the brand’s voice, content and growth.</p></div>
          <div><h6>{p.d.name}</h6><ul><li>{p.d.url}</li><li>{p.d.aud}</li><li>Brand Persona · Edition 01</li></ul></div>
          <div><h6>100XAI</h6><ul><li>Growth · Automation · Brand</li><li>LinkedIn · SEO · Content</li><li>100xai.co</li></ul></div>
        </div>
        <div className="pz-fine"><span>© {p.year} · Prepared by 100XAI for {p.d.name}</span><span>Brand Persona · Vol. I · Edition 01</span></div>
      </div></footer>

      <div className="pz-cta"><div className="pz-cta-inner">
        <div className="eyebrow">Your persona is ready</div>
        <h2>Now let&apos;s <span className="it">fill the calendar.</span></h2>
        <p>Turn this persona into a month of on-brand blogs, LinkedIn posts and Instagram content — planned, approved and auto-scheduled, all in your voice.</p>
        <button className="pz-cta-btn" onClick={goPlanner}>Start creating &amp; scheduling content for {p.d.name} →</button>
        <div><span className="alt" onClick={goEdit}>Tweak the persona first</span></div>
      </div></div>
    </section>
  );
}
