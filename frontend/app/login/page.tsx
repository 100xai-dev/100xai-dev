"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const doLogin = () => router.push("/brands");

  return (
    <div className="login-screen">
      <div className="login-art">
        <div className="glow" />
        <div className="grid-bg" />
        <div className="brand"><span className="dot" />Schedu<b>lr</b></div>
        <div className="art-quote">
          <h2>Your content<br />pipeline, on <span className="accent">autopilot.</span></h2>
          <p>Sign in to plan, draft and publish across every channel from a single calendar.</p>
          <div className="mini-cal">
            <div className="mc"><div className="d">MON</div><div className="bar" style={{ background: "var(--blog)" }} /></div>
            <div className="mc"><div className="d">TUE</div><div className="bar" style={{ background: "var(--li)" }} /></div>
            <div className="mc"><div className="d">WED</div><div className="bar" style={{ background: "var(--ig)" }} /></div>
            <div className="mc"><div className="d">THU</div><div className="bar" style={{ background: "var(--li)" }} /></div>
            <div className="mc"><div className="d">FRI</div><div className="bar" style={{ background: "var(--blog)" }} /></div>
          </div>
        </div>
      </div>
      <div className="login-form-wrap">
        <Link className="back-home" href="/">← Back to site</Link>
        <div className="login-form">
          <div className="brand"><span className="dot" />Schedu<b>lr</b></div>
          <h3>Welcome back</h3>
          <p className="sub">Sign in to your 100xAI workspace.</p>
          <div className="field">
            <label>Work email</label>
            <input type="email" defaultValue="rajeev@100xai.co" placeholder="you@100xai.co" />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" defaultValue="demo1234" placeholder="••••••••" />
          </div>
          <button className="btn btn-red" onClick={doLogin}>Sign in →</button>
          <div className="divider">or continue with</div>
          <div className="sso">
            <button onClick={doLogin}>Google</button>
            <button onClick={doLogin}>SSO</button>
          </div>
          <div className="login-alt">No account yet? <a onClick={doLogin}>Request access</a></div>
        </div>
      </div>
    </div>
  );
}
