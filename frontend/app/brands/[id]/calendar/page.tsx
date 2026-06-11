"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";


interface ScheduleItem {
  id: string;
  title: string;
  scheduled_at: string;
  status: string;
  target_keyword: string | null;
  blog_job_id: string | null;
  published_urls?: Record<string, string> | null;
  last_error?: string | null;
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];

const CHIP: Record<string, { bg: string; text: string; dot: string }> = {
  SCHEDULED:  { bg: "#e3f2fd", text: "#1565c0", dot: "#1e88e5" },
  PENDING_APPROVAL: { bg: "#fff8e1", text: "#a76f00", dot: "#f5a623" },
  PUBLISHING: { bg: "#fff3e0", text: "#e65100", dot: "#fb8c00" },
  PUBLISHED:  { bg: "#e8f5e9", text: "#2e7d32", dot: "#43a047" },
  FAILED:     { bg: "#ffebee", text: "#b71c1c", dot: "#e53935" },
  DRAFT:      { bg: "#f3e5f5", text: "#6a1b9a", dot: "#8e24aa" },
  CANCELLED:  { bg: "#eceff1", text: "#546e7a", dot: "#90a4ae" },
  default:    { bg: "#f3e5f5", text: "#6a1b9a", dot: "#8e24aa" },
};
const chipStyle = (s: string) => CHIP[s] ?? CHIP.default;

function ymd(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
function isToday(d: Date) {
  return isSameDay(d, new Date());
}
function isPast(d: Date) {
  const t = new Date();
  t.setHours(0, 0, 0, 0);
  return d < t;
}
function buildGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const start = new Date(first);
  start.setDate(start.getDate() - first.getDay());
  const end = new Date(last);
  end.setDate(end.getDate() + (6 - last.getDay()));
  const days: Date[] = [];
  const cur = new Date(start);
  while (cur <= end) {
    days.push(new Date(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return days;
}


export default function CalendarPage() {
  const params = useParams();
  const brandId = params.id as string;

  const [cur, setCur] = useState(new Date());
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Multi-day selection + scheduling modal
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showModal, setShowModal] = useState(false);
  const [keywords, setKeywords] = useState<Record<string, string>>({});
  const [time, setTime] = useState("09:00");
  const [submitting, setSubmitting] = useState(false);
  const [detail, setDetail] = useState<ScheduleItem | null>(null);

  const year = cur.getFullYear();
  const month = cur.getMonth();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/schedules/brands/${brandId}/calendar?year=${year}&month=${month + 1}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      setItems(await res.json());
    } catch (e) {
      setError("Could not load calendar — " + (e instanceof Error ? e.message : "unknown error"));
    } finally {
      setLoading(false);
    }
  }, [brandId, year, month]);

  useEffect(() => { load(); }, [load]);

  const grid = buildGrid(year, month);
  const itemsOn = (day: Date) => items.filter((e) => isSameDay(new Date(e.scheduled_at), day));

  function nav(dir: -1 | 1) {
    setCur((p) => { const n = new Date(p); n.setMonth(n.getMonth() + dir); return n; });
  }

  function toggleDay(day: Date) {
    if (isPast(day)) return; // can't schedule in the past
    const key = ymd(day);
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  function openScheduleModal() {
    const kw: Record<string, string> = {};
    for (const d of selected) kw[d] = keywords[d] ?? "";
    setKeywords(kw);
    setShowModal(true);
  }

  async function submitSchedule() {
    const entries = Array.from(selected).sort();
    const payloadItems = entries
      .map((date) => ({ date, keyword: (keywords[date] ?? "").trim() }))
      .filter((it) => it.keyword.length > 0);

    if (payloadItems.length === 0) {
      setError("Enter a keyword for at least one selected day.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const res = await fetch(`/api/v1/schedules/brands/${brandId}/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: payloadItems, time, timezone: tz, channels: ["wordpress"] }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : `API error ${res.status}`);
      }
      setShowModal(false);
      setSelected(new Set());
      setKeywords({});
      await load();
    } catch (e) {
      setError("Could not schedule — " + (e instanceof Error ? e.message : "unknown error"));
    } finally {
      setSubmitting(false);
    }
  }

  async function reviewAction(scheduleId: string, action: "approve" | "reject") {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/schedules/${scheduleId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: action === "reject" ? JSON.stringify({ reason: "Rejected from calendar" }) : undefined,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : `API error ${res.status}`);
      }
      setDetail(null);
      await load();
    } catch (e) {
      setError(`Could not ${action} — ` + (e instanceof Error ? e.message : "unknown error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#f8f9fa", fontFamily: "Google Sans, Roboto, sans-serif" }}>
      {/* Toolbar */}
      <div style={{ background: "#fff", borderBottom: "1px solid #dadce0", padding: "12px 24px", display: "flex", alignItems: "center", gap: 16, position: "sticky", top: 0, zIndex: 10 }}>
        <span style={{ fontSize: 22, marginRight: 4 }}>📅</span>
        <span style={{ fontSize: 20, fontWeight: 600, color: "#3c4043", marginRight: 16 }}>Content Calendar</span>
        <button onClick={() => setCur(new Date())} style={{ padding: "6px 16px", border: "1px solid #dadce0", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 14, color: "#3c4043", fontWeight: 500 }}>Today</button>
        <div style={{ display: "flex", gap: 4 }}>
          {([-1, 1] as const).map((dir) => (
            <button key={dir} onClick={() => nav(dir)} style={{ width: 32, height: 32, border: "none", background: "transparent", cursor: "pointer", borderRadius: "50%", fontSize: 18, color: "#5f6368", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {dir === -1 ? "‹" : "›"}
            </button>
          ))}
        </div>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 400, color: "#3c4043" }}>{MONTHS[month]} {year}</h2>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 13, color: "#5f6368" }}>Click days to schedule →</span>
        <Link href={`/brands/${brandId}/review`} style={{ padding: "8px 18px", background: "#fff", color: "#a76f00", border: "1px solid #f5a623", borderRadius: 24, fontSize: 14, fontWeight: 500, textDecoration: "none" }}>Review queue</Link>
        <Link href={`/brands/${brandId}/blogs/new`} style={{ padding: "8px 18px", background: "#fff", color: "#1a73e8", border: "1px solid #dadce0", borderRadius: 24, fontSize: 14, fontWeight: 500, textDecoration: "none" }}>+ One-off Article</Link>
      </div>

      {error && (
        <div style={{ margin: "12px 24px", padding: "10px 16px", background: "#fff3cd", border: "1px solid #ffc107", borderRadius: 6, color: "#856404", fontSize: 14 }}>
          {error} — <button onClick={load} style={{ background: "none", border: "none", color: "#1a73e8", cursor: "pointer", fontSize: 14, padding: 0 }}>Retry</button>
        </div>
      )}

      {/* Calendar */}
      <div style={{ padding: "0 24px 100px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", borderBottom: "1px solid #dadce0" }}>
          {DAYS.map((d) => (
            <div key={d} style={{ padding: "8px 0", textAlign: "center", fontSize: 11, fontWeight: 500, color: "#70757a", letterSpacing: "0.5px", textTransform: "uppercase" }}>{d}</div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", border: "1px solid #dadce0", borderTop: "none" }}>
          {loading
            ? Array.from({ length: 35 }).map((_, i) => (
                <div key={i} style={{ minHeight: 110, borderRight: "1px solid #dadce0", borderBottom: "1px solid #dadce0", padding: 8, background: "#fff" }}>
                  <div style={{ width: 24, height: 24, borderRadius: "50%", background: "#f1f3f4", marginBottom: 6 }} />
                </div>
              ))
            : grid.map((day, i) => {
                const inMonth = day.getMonth() === month;
                const today = isToday(day);
                const past = isPast(day);
                const key = ymd(day);
                const isSel = selected.has(key);
                const chips = itemsOn(day);
                return (
                  <div
                    key={i}
                    onClick={() => toggleDay(day)}
                    style={{
                      minHeight: 110,
                      borderRight: "1px solid #dadce0",
                      borderBottom: "1px solid #dadce0",
                      padding: "6px 4px 4px",
                      background: isSel ? "#e8f0fe" : today ? "#f1f7ff" : "#fff",
                      boxShadow: isSel ? "inset 0 0 0 2px #1a73e8" : "none",
                      opacity: inMonth ? 1 : 0.4,
                      position: "relative",
                      cursor: past ? "default" : "pointer",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "center", marginBottom: 4 }}>
                      <span style={{ width: 26, height: 26, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: today ? 700 : 400, background: today ? "#1a73e8" : "transparent", color: today ? "#fff" : inMonth ? "#3c4043" : "#9aa0a6" }}>
                        {day.getDate()}
                      </span>
                    </div>
                    {isSel && (
                      <span style={{ position: "absolute", top: 6, right: 8, fontSize: 12, color: "#1a73e8", fontWeight: 700 }}>✓</span>
                    )}

                    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                      {chips.slice(0, 3).map((ev) => {
                        const c = chipStyle(ev.status);
                        return (
                          <button key={ev.id} onClick={(e) => { e.stopPropagation(); setDetail(ev); }} title={ev.title}
                            style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 6px", borderRadius: 4, background: c.bg, border: "none", cursor: "pointer", textAlign: "left", width: "100%" }}>
                            <span style={{ width: 6, height: 6, borderRadius: "50%", background: c.dot, flexShrink: 0 }} />
                            <span style={{ fontSize: 11, fontWeight: 500, color: c.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                              {ev.title.length > 22 ? ev.title.slice(0, 22) + "…" : ev.title}
                            </span>
                          </button>
                        );
                      })}
                      {chips.length > 3 && <span style={{ fontSize: 10, color: "#70757a", paddingLeft: 6 }}>+{chips.length - 3} more</span>}
                    </div>
                  </div>
                );
              })}
        </div>
      </div>

      {/* Floating action bar when days are selected */}
      {selected.size > 0 && !showModal && (
        <div style={{ position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)", background: "#202124", color: "#fff", borderRadius: 28, padding: "10px 14px 10px 22px", display: "flex", alignItems: "center", gap: 14, boxShadow: "0 6px 24px rgba(0,0,0,0.3)", zIndex: 40 }}>
          <span style={{ fontSize: 14 }}>{selected.size} day{selected.size > 1 ? "s" : ""} selected</span>
          <button onClick={() => setSelected(new Set())} style={{ background: "none", border: "none", color: "#bdc1c6", cursor: "pointer", fontSize: 13 }}>Clear</button>
          <button onClick={openScheduleModal} style={{ background: "#1a73e8", color: "#fff", border: "none", borderRadius: 20, padding: "8px 18px", fontSize: 14, fontWeight: 500, cursor: "pointer" }}>
            Schedule {selected.size} day{selected.size > 1 ? "s" : ""} →
          </button>
        </div>
      )}

      {/* Scheduling modal: one keyword per day + one time */}
      {showModal && (
        <div onClick={() => !submitting && setShowModal(false)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "#fff", borderRadius: 10, boxShadow: "0 8px 40px rgba(0,0,0,0.2)", padding: 24, width: 520, maxWidth: "92vw", maxHeight: "85vh", overflowY: "auto" }}>
            <h3 style={{ margin: "0 0 4px", fontSize: 18, fontWeight: 600, color: "#202124" }}>Schedule content</h3>
            <p style={{ margin: "0 0 16px", fontSize: 13, color: "#5f6368" }}>
              Each article is generated now. Once ready it goes to the{" "}
              <strong>review queue</strong> for approval — nothing is published until you approve it.
              The time below is the target publish slot.
            </p>

            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <label style={{ fontSize: 13, color: "#3c4043", fontWeight: 500 }}>Publish time (all days):</label>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)}
                style={{ padding: "6px 10px", border: "1px solid #dadce0", borderRadius: 6, fontSize: 14 }} />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {Array.from(selected).sort().map((date) => {
                const d = new Date(date + "T00:00:00");
                return (
                  <div key={date} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ width: 130, flexShrink: 0, fontSize: 13, color: "#3c4043", fontWeight: 500 }}>
                      {d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
                    </span>
                    <input
                      autoFocus={date === Array.from(selected).sort()[0]}
                      placeholder="keyword / topic for this day"
                      value={keywords[date] ?? ""}
                      onChange={(e) => setKeywords((p) => ({ ...p, [date]: e.target.value }))}
                      style={{ flex: 1, padding: "8px 12px", border: "1px solid #dadce0", borderRadius: 6, fontSize: 14 }}
                    />
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: 22, display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowModal(false)} disabled={submitting} style={{ padding: "9px 18px", border: "1px solid #dadce0", borderRadius: 6, background: "#fff", fontSize: 14, cursor: "pointer", color: "#3c4043" }}>Cancel</button>
              <button onClick={submitSchedule} disabled={submitting} style={{ padding: "9px 20px", border: "none", borderRadius: 6, background: submitting ? "#8ab4f8" : "#1a73e8", color: "#fff", fontSize: 14, fontWeight: 500, cursor: submitting ? "default" : "pointer" }}>
                {submitting ? "Scheduling…" : "Schedule & Generate"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Detail popover for an existing scheduled item */}
      {detail && (
        <div onClick={() => setDetail(null)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "#fff", borderRadius: 8, boxShadow: "0 8px 40px rgba(0,0,0,0.2)", padding: 24, width: 400, maxWidth: "90vw" }}>
            <div style={{ height: 6, borderRadius: "4px 4px 0 0", background: chipStyle(detail.status).dot, margin: "-24px -24px 16px" }} />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: chipStyle(detail.status).dot, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 4 }}>{detail.status.replace(/_/g, " ")}</div>
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600, color: "#202124" }}>{detail.title}</h3>
              </div>
              <button onClick={() => setDetail(null)} style={{ border: "none", background: "none", cursor: "pointer", fontSize: 20, color: "#5f6368", lineHeight: 1 }}>✕</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13, color: "#5f6368" }}>
              <div style={{ display: "flex", gap: 10 }}><span>📅</span><span>{new Date(detail.scheduled_at).toLocaleString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric", hour: "numeric", minute: "2-digit" })}</span></div>
              {detail.target_keyword && <div style={{ display: "flex", gap: 10 }}><span>🔑</span><span>Keyword: <strong style={{ color: "#3c4043" }}>{detail.target_keyword}</strong></span></div>}
              {detail.last_error && <div style={{ display: "flex", gap: 10, color: "#b71c1c" }}><span>⚠️</span><span>{detail.last_error}</span></div>}
              {detail.published_urls?.wordpress && <div style={{ display: "flex", gap: 10 }}><span>🔗</span><a href={detail.published_urls.wordpress} target="_blank" rel="noreferrer" style={{ color: "#1a73e8" }}>View published post</a></div>}
            </div>
            <div style={{ marginTop: 20, display: "flex", gap: 10, justifyContent: "flex-end" }}>
              {detail.status === "PENDING_APPROVAL" && (
                <>
                  <button onClick={() => reviewAction(detail.id, "reject")} disabled={submitting} style={{ padding: "8px 18px", border: "1px solid #e53935", borderRadius: 4, background: "#fff", fontSize: 13, fontWeight: 500, cursor: submitting ? "default" : "pointer", color: "#b71c1c" }}>Reject</button>
                  <button onClick={() => reviewAction(detail.id, "approve")} disabled={submitting} style={{ padding: "8px 18px", border: "none", borderRadius: 4, background: submitting ? "#a5d6a7" : "#2e7d32", color: "#fff", fontSize: 13, fontWeight: 500, cursor: submitting ? "default" : "pointer" }}>Approve & Publish</button>
                </>
              )}
              {detail.blog_job_id && (
                <Link href={`/brands/${brandId}/blogs/${detail.blog_job_id}`} onClick={() => setDetail(null)} style={{ padding: "8px 18px", background: "#1a73e8", color: "#fff", borderRadius: 4, fontSize: 13, fontWeight: 500, textDecoration: "none" }}>Open Article →</Link>
              )}
              <button onClick={() => setDetail(null)} style={{ padding: "8px 18px", border: "1px solid #dadce0", borderRadius: 4, background: "#fff", fontSize: 13, cursor: "pointer", color: "#3c4043" }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
