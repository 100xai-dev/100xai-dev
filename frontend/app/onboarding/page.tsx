"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { useScheduler } from "@/lib/scheduler/context";
import {
  ACCENT_SWATCHES, cleanDomain, DEFAULT_BRAND, isValidDomain, TONE_OPTIONS, type BrandData,
} from "@/lib/scheduler/persona";

export default function OnboardingPage() {
  const router = useRouter();
  const { setBrand } = useScheduler();

  const [name, setName] = useState(DEFAULT_BRAND.name);
  const [url, setUrl] = useState(DEFAULT_BRAND.domain);
  const [one, setOne] = useState(DEFAULT_BRAND.one);
  const [aud, setAud] = useState(DEFAULT_BRAND.aud);
  const [tone, setTone] = useState<string[]>(DEFAULT_BRAND.tone);
  const [founder, setFounder] = useState(DEFAULT_BRAND.founder);
  const [role, setRole] = useState(DEFAULT_BRAND.role);
  const [mission, setMission] = useState(DEFAULT_BRAND.mission);
  const [accent, setAccent] = useState(DEFAULT_BRAND.accent);
  const [urlErr, setUrlErr] = useState(false);

  const [genActive, setGenActive] = useState(false);
  const [genStep, setGenStep] = useState("Connecting…");
  const [genWidth, setGenWidth] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const toggleTone = (t: string) =>
    setTone((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));

  const generate = () => {
    const dom = cleanDomain(url);
    if (!isValidDomain(dom)) {
      setUrlErr(true);
      return;
    }
    setUrlErr(false);

    const data: BrandData = {
      name: name.trim() || dom.split(".")[0],
      domain: dom,
      url: "https://" + dom,
      one: one.trim() || "a brand on a mission",
      aud: aud.trim() || "the people we serve",
      tone,
      founder: founder.trim() || "The Founder",
      role: role.trim() || "Founder",
      mission: mission.trim() || "a future worth building",
      accent,
    };
    setBrand(data);

    const steps = [
      `Connecting to ${dom}…`, "Reading brand signals…", "Mapping voice & values…",
      "Deriving the palette…", "Composing the persona…",
    ];
    setGenActive(true);
    setGenWidth(0);
    setGenStep(steps[0]);
    let i = 0;
    timer.current = setInterval(() => {
      i++;
      setGenWidth(Math.min(100, (i / steps.length) * 100));
      if (i < steps.length) {
        setGenStep(steps[i]);
      } else {
        if (timer.current) clearInterval(timer.current);
        setGenStep("Done");
        setTimeout(() => router.push("/persona"), 480);
      }
    }, 680);
  };

  return (
    <section id="onboard">
      <div className="ob-wrap">
        <div className="ob-top">
          <div className="brand"><span className="dot" />Schedu<b>lr</b></div>
          <div className="ob-skip" onClick={() => router.push("/planner")}>Skip for now →</div>
        </div>
        <div className="ob-eyebrow">Step 1 · Brand setup</div>
        <h1 className="ob-title">Let&apos;s compose your <span className="it">brand persona.</span></h1>
        <p className="ob-sub">
          Point us to your site and answer a few essentials. The engine reads your brand and composes a living
          persona — voice, values, founder and palette in one page. Then you start scheduling.
        </p>

        <div className="ob-card">
          <div className="ob-field">
            <label>Brand name</label>
            <input className="ob-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Roadveer" />
          </div>
          <div className="ob-field">
            <label>Website <span className="hint">https required</span></label>
            <div className="ob-url">
              <span className="pre">https://</span>
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="yourbrand.com" />
            </div>
            <div className={`ob-err${urlErr ? " show" : ""}`}>Please enter a valid website, e.g. yourbrand.com</div>
          </div>
          <div className="ob-field">
            <label>What does your brand do? <span className="hint">one line</span></label>
            <input className="ob-input" value={one} onChange={(e) => setOne(e.target.value)} placeholder="We…" />
          </div>
          <div className="ob-field">
            <label>Who is it for?</label>
            <input className="ob-input" value={aud} onChange={(e) => setAud(e.target.value)} placeholder="Your audience" />
          </div>
          <div className="ob-field">
            <label>Brand voice <span className="hint">pick a few</span></label>
            <div className="ob-chips">
              {TONE_OPTIONS.map((t) => (
                <div key={t} className={`ob-chip${tone.includes(t) ? " on" : ""}`} onClick={() => toggleTone(t)}>{t}</div>
              ))}
            </div>
          </div>
          <div className="ob-two">
            <div className="ob-field"><label>Founder name</label><input className="ob-input" value={founder} onChange={(e) => setFounder(e.target.value)} placeholder="Full name" /></div>
            <div className="ob-field"><label>Founder role</label><input className="ob-input" value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Founder & CEO" /></div>
          </div>
          <div className="ob-field">
            <label>Mission / what you&apos;re building toward</label>
            <textarea className="ob-textarea" value={mission} onChange={(e) => setMission(e.target.value)} placeholder="Our mission…" />
          </div>
          <div className="ob-field">
            <label>Brand accent colour</label>
            <div className="ob-swatches">
              {ACCENT_SWATCHES.map((c) => (
                <span key={c} className={`ob-sw${accent === c ? " on" : ""}`} style={{ background: c }} onClick={() => setAccent(c)} />
              ))}
              <label className="ob-sw-custom">＋
                <input type="color" value={accent} onChange={(e) => setAccent(e.target.value)} />
              </label>
            </div>
          </div>
          <div className="ob-actions">
            <button className="btn btn-red" onClick={generate}>Generate brand persona</button>
          </div>
          <div className="ob-note">Takes a few seconds · You can edit anything afterwards</div>
        </div>
      </div>

      <div className={`gen-overlay${genActive ? " show" : ""}`}>
        <div className="gen-spinner">
          <svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="none" stroke="var(--border)" strokeWidth="3.5" />
            <circle cx="32" cy="32" r="28" fill="none" stroke="var(--accent)" strokeWidth="3.5" strokeDasharray="46 130" strokeLinecap="round" />
          </svg>
        </div>
        <div className="gen-title">Composing your <span className="it">brand persona</span></div>
        <div className="gen-steps">{genStep}</div>
        <div className="gen-bar"><span style={{ width: `${genWidth}%` }} /></div>
      </div>
    </section>
  );
}
