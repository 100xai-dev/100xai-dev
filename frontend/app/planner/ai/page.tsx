"use client";

import Link from "next/link";

import { useScheduler } from "@/lib/scheduler/context";

export default function AIStudioPage() {
  const { showToast } = useScheduler();
  return (
    <div className="page-pad">
      <div className="ai-hero">
        <div className="glow" />
        <div className="badge">Roadmap · v1.0</div>
        <h2>From a topic to a <span className="it">published month</span> — automatically.</h2>
        <p>AI Studio is the next layer of Schedulr. Hand it a topic, a content pillar, or a product URL — it researches, writes in your brand voice, generates the visuals, and drops finished drafts straight into the calendar for approval.</p>
        <div className="ai-steps">
          <div className="ai-step"><div className="sn">01</div><h4>Brief</h4><p>Pick a pillar (Driver Dignity, Highway Help, Vendor Growth…) or paste a topic. Set tone &amp; channel.</p></div>
          <div className="ai-step"><div className="sn">02</div><h4>Generate</h4><p>The n8n engine researches via Serper, writes brand-voice copy, and creates KIE/Seedance visuals.</p></div>
          <div className="ai-step"><div className="sn">03</div><h4>Auto-schedule</h4><p>Drafts slot into your calendar at high-engagement times, gated by WhatsApp approval.</p></div>
        </div>
        <div className="flow-vis">
          <span className="flow-node on">Topic</span><span className="flow-arrow">→</span>
          <span className="flow-node">Research</span><span className="flow-arrow">→</span>
          <span className="flow-node">Brand-voice draft</span><span className="flow-arrow">→</span>
          <span className="flow-node">Visuals</span><span className="flow-arrow">→</span>
          <span className="flow-node">Calendar</span><span className="flow-arrow">→</span>
          <span className="flow-node on">Approve &amp; publish</span>
        </div>
        <div className="ai-cta-row">
          <button className="btn btn-red" onClick={() => showToast("You are on the v1.0 early-access list.", true)}>Join early access</button>
          <Link className="btn btn-ghost" href="/planner">Back to planner</Link>
        </div>
      </div>
    </div>
  );
}
