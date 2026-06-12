import Link from "next/link";

export default function HomePage() {
  return (
    <div id="home">
      <nav className="top">
        <div className="brand"><span className="dot" />Schedu<b>lr</b></div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a>Pricing</a>
          <a>Docs</a>
          <Link href="/login">Sign in</Link>
          <Link className="btn btn-red" href="/login">Launch App →</Link>
        </div>
      </nav>

      <section className="hero">
        <div className="tag"><span className="pulse" /> By 100xAI · Content Automation</div>
        <h1 className="hero-title">
          Schedule <span className="accent">everything.</span><br />
          Everywhere. <span className="underline">Once.</span>
        </h1>
        <p className="sub">
          One calendar for your blogs, LinkedIn, and Instagram. <span className="em">Plan a month of content in minutes</span>,
          drag-and-drop to reschedule, and let AI write &amp; queue it for you — built on the 100xAI automation stack.
        </p>
        <div className="hero-cta">
          <Link className="btn btn-red" href="/login">Open the Planner →</Link>
          <a className="btn btn-ghost" href="#features">See how it works</a>
        </div>

        <div className="hero-meta">
          <div className="m"><b>3</b><span>Networks unified</span></div>
          <div className="m"><b>30d</b><span>Planned ahead</span></div>
          <div className="m"><b>1-click</b><span>AI draft &amp; queue</span></div>
          <div className="m"><b>∞</b><span>Posts / month</span></div>
        </div>

        <div className="platforms-strip">
          Publishes to
          <span className="pf-chip"><span className="pf-ic" style={{ background: "var(--blog)" }}>B</span> Blog / Shopify</span>
          <span className="pf-chip"><span className="pf-ic" style={{ background: "var(--li)" }}>in</span> LinkedIn</span>
          <span className="pf-chip"><span className="pf-ic" style={{ background: "var(--ig)" }}>ig</span> Instagram</span>
        </div>
      </section>

      <section className="features" id="features">
        <div className="sec-label">The workflow</div>
        <h2 className="sec-title">Plan, approve, publish — <span className="it">without the tab juggling.</span></h2>
        <div className="feat-grid">
          <div className="feat-card">
            <h3>Unified content calendar</h3>
            <p>A Hootsuite-style planner that shows your blog, LinkedIn and Instagram pipeline side-by-side. Switch between week, month and list views instantly.</p>
          </div>
          <div className="feat-card">
            <h3>Drag-to-reschedule</h3>
            <p>Move a post to a new day or time by dragging it across the grid. The queue rebalances itself — no forms, no re-typing.</p>
          </div>
          <div className="feat-card">
            <h3>Approval-gated publishing</h3>
            <p>Route drafts through WhatsApp / team approval before anything goes live. Built to match the 100xAI client review flow.</p>
          </div>
          <div className="feat-card soon">
            <h3>AI blog generation</h3>
            <p>Give a topic or title — the engine researches, writes a brand-voice blog, and drops it straight into the calendar as a draft.</p>
          </div>
          <div className="feat-card soon">
            <h3>Auto-schedule queue</h3>
            <p>Set your cadence once. AI generates a month of posts per pillar and auto-slots them into your best-performing time windows.</p>
          </div>
          <div className="feat-card soon">
            <h3>Performance loop</h3>
            <p>Analytics feed back into scheduling — the system learns what lands and shifts your queue toward higher-engagement slots.</p>
          </div>
        </div>
      </section>

      <footer className="home-foot">
        <div className="brand" style={{ fontSize: 16 }}><span className="dot" style={{ width: 24, height: 24 }} />Schedu<b>lr</b></div>
        <div>© 2026 100xAI · Built on n8n + KIE + ElevenLabs automation</div>
        <div className="mono">v0.9 · BETA</div>
      </footer>
    </div>
  );
}
