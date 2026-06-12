"use client";

import { PF, useScheduler } from "@/lib/scheduler/context";
import type { PlatformKey } from "@/lib/scheduler/data";

const PICKS: { pf: PlatformKey; label: string }[] = [
  { pf: "blog", label: "Blog" },
  { pf: "li", label: "LinkedIn" },
  { pf: "ig", label: "Instagram" },
];

export default function ComposeModal() {
  const {
    brand, compose, closeCompose, updateCompose, toggleComposeChannel, submitCompose, showToast,
  } = useScheduler();

  const channelNames = compose.channels.map((p) => PF[p].name).join(" · ") || "No channel";
  const av = (brand.name.trim()[0] || "R").toUpperCase();

  return (
    <div
      className={`modal-bg${compose.open ? " open" : ""}`}
      onClick={(e) => { if (e.target === e.currentTarget) closeCompose(); }}
    >
      <div className="modal">
        <div className="modal-left">
          <div className="modal-head">
            <h3>{compose.title}</h3>
            <button className="modal-close" onClick={closeCompose}>×</button>
          </div>

          <div className="platform-pick">
            {PICKS.map(({ pf, label }) => (
              <div
                key={pf}
                className={`pp${compose.channels.includes(pf) ? " sel" : ""}`}
                onClick={() => toggleComposeChannel(pf)}
              >
                <div className="ppic" style={{ background: PF[pf].bg }}>{PF[pf].ic}</div>
                <div className="ppn">{label}</div>
              </div>
            ))}
          </div>

          <textarea
            className="compose-area"
            placeholder="What do you want to share?"
            value={compose.text}
            onChange={(e) => updateCompose({ text: e.target.value })}
          />
          <div className="compose-tools">
            <button className="tool-btn">Media</button>
            <button className="tool-btn">Hashtags</button>
            <button className="tool-btn">Emoji</button>
            <button
              className="tool-btn ai"
              onClick={() => showToast("AI blog generation lands in v1.0 — topic-to-draft, auto-queued.", true)}
            >
              Generate with AI <span style={{ fontFamily: "var(--mono)", fontSize: 9, opacity: 0.7 }}>SOON</span>
            </button>
            <span className="char-count">{compose.text.length}</span>
          </div>

          <div className="schedule-block">
            <div className="sbl">Schedule</div>
            <div className="dt-row">
              <input type="date" value={compose.date} onChange={(e) => updateCompose({ date: e.target.value })} />
              <input type="time" value={compose.time} onChange={(e) => updateCompose({ time: e.target.value })} />
            </div>
          </div>

          <div className="modal-actions">
            <button className="btn btn-soft" onClick={closeCompose}>Save as draft</button>
            <button className="btn btn-red" onClick={submitCompose}>Schedule post →</button>
          </div>
        </div>

        <div className="modal-right">
          <div className="prv-label">Live preview</div>
          <div className="preview-card">
            <div className="prev-head">
              <div className="pav">{av}</div>
              <div>
                <div className="pn">{brand.name} · 100xAI</div>
                <div className="ph2">{channelNames} · {compose.editingId != null ? "editing" : "new"}</div>
              </div>
            </div>
            <div className="prev-text">{compose.text || "Your post will appear here…"}</div>
            <div className="prev-img">Media preview</div>
          </div>
        </div>
      </div>
    </div>
  );
}
