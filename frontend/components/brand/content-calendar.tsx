"use client";

import { useState } from "react";

import { createSchedulesBulk, deleteSchedule, getBrandCalendar } from "@/lib/api";
import type { BrandStatus, CalendarEntry } from "@/lib/types";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function localDateStr(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function timePart(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

type ComposeRow = { id: number; date: string; keyword: string };

export function ContentCalendar({
  brandId,
  brandStatus,
  initialYear,
  initialMonth,
  initialEntries,
}: {
  brandId: string;
  brandStatus: BrandStatus;
  initialYear: number;
  initialMonth: number; // 1-12
  initialEntries: CalendarEntry[];
}) {
  const [year, setYear] = useState(initialYear);
  const [month, setMonth] = useState(initialMonth);
  const [entries, setEntries] = useState<CalendarEntry[]>(initialEntries);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Compose state
  const [rows, setRows] = useState<ComposeRow[]>([{ id: 1, date: "", keyword: "" }]);
  const [time, setTime] = useState("10:00");
  const [submitting, setSubmitting] = useState(false);

  const canSchedule = brandStatus === "READY";
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

  async function loadMonth(y: number, m: number) {
    setLoading(true);
    setError("");
    try {
      const data = await getBrandCalendar(brandId, y, m);
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load calendar");
    } finally {
      setLoading(false);
    }
  }

  function shiftMonth(dir: number) {
    let m = month + dir;
    let y = year;
    if (m < 1) { m = 12; y -= 1; }
    if (m > 12) { m = 1; y += 1; }
    setYear(y);
    setMonth(m);
    void loadMonth(y, m);
  }

  function addRow() {
    setRows((r) => [...r, { id: (r[r.length - 1]?.id ?? 0) + 1, date: "", keyword: "" }]);
  }
  function updateRow(id: number, patch: Partial<ComposeRow>) {
    setRows((r) => r.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }
  function removeRow(id: number) {
    setRows((r) => (r.length === 1 ? r : r.filter((row) => row.id !== id)));
  }

  async function onSchedule(e: React.FormEvent) {
    e.preventDefault();
    const items = rows
      .map((r) => ({ date: r.date.trim(), keyword: r.keyword.trim() }))
      .filter((r) => r.date && r.keyword);
    if (items.length === 0) {
      setError("Add at least one row with a date and keyword.");
      return;
    }
    setSubmitting(true);
    setError("");
    setNotice("");
    try {
      const res = await createSchedulesBulk(brandId, {
        items,
        time,
        timezone_str: tz,
        channels: ["wordpress"],
      });
      setNotice(`Scheduled ${res.count} post(s). Generation has started; each will auto-publish at ${time}.`);
      setRows([{ id: 1, date: "", keyword: "" }]);
      await loadMonth(year, month);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to schedule content");
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(entry: CalendarEntry) {
    if (entry.status === "PUBLISHED") return;
    if (!window.confirm(`Cancel scheduled post "${entry.title}"?`)) return;
    try {
      await deleteSchedule(entry.id);
      setEntries((prev) => prev.filter((e) => e.id !== entry.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete schedule");
    }
  }

  // Build month grid (Monday-first).
  const first = new Date(year, month - 1, 1);
  const lead = (first.getDay() + 6) % 7; // 0 = Monday
  const daysInMonth = new Date(year, month, 0).getDate();
  const todayStr = localDateStr(new Date());

  const cells: { day: number | null; dateStr: string | null }[] = [];
  for (let i = 0; i < lead; i++) cells.push({ day: null, dateStr: null });
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ day: d, dateStr: localDateStr(new Date(year, month - 1, d)) });
  }
  while (cells.length % 7 !== 0) cells.push({ day: null, dateStr: null });

  const byDate = new Map<string, CalendarEntry[]>();
  for (const e of entries) {
    const key = localDateStr(new Date(e.scheduled_at));
    const list = byDate.get(key) ?? [];
    list.push(e);
    byDate.set(key, list);
  }

  return (
    <div className="stack stack-lg">
      {error && <div className="alert alert-danger">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {/* Schedule composer */}
      {canSchedule ? (
        <form className="card stack" onSubmit={onSchedule}>
          <div className="section-heading" style={{ margin: 0 }}>Schedule blog content</div>
          <p className="meta">
            Each row generates an article for the keyword and auto-publishes to WordPress on the chosen day at the set time.
          </p>

          <div className="stack stack-sm">
            {rows.map((row) => (
              <div key={row.id} style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <input
                  type="date"
                  value={row.date}
                  onChange={(e) => updateRow(row.id, { date: e.target.value })}
                  style={{ width: 170 }}
                />
                <input
                  value={row.keyword}
                  onChange={(e) => updateRow(row.id, { keyword: e.target.value })}
                  placeholder="Target keyword"
                  style={{ flex: 1, minWidth: 200 }}
                />
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => removeRow(row.id)}
                  style={{ padding: "10px 14px" }}
                  disabled={rows.length === 1}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" className="btn-secondary" onClick={addRow}>+ Add row</button>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 500 }}>
              <span className="meta" style={{ margin: 0 }}>Publish time</span>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} style={{ width: 130 }} />
            </label>
            <span className="meta">{tz}</span>
            <button type="submit" disabled={submitting} style={{ marginLeft: "auto" }}>
              {submitting ? "Scheduling…" : "Schedule & Generate"}
            </button>
          </div>
        </form>
      ) : (
        <div className="alert alert-warning">
          <span>⚠</span>
          <span>The brand must be READY before scheduling content. Current status: <strong>{brandStatus}</strong>.</span>
        </div>
      )}

      {/* Month nav */}
      <div className="row">
        <div className="section-heading" style={{ margin: 0 }}>
          {MONTHS[month - 1]} {year}
        </div>
        <div className="action-row">
          <button type="button" className="btn-secondary" onClick={() => shiftMonth(-1)} disabled={loading}>‹ Prev</button>
          <button type="button" className="btn-secondary" onClick={() => shiftMonth(1)} disabled={loading}>Next ›</button>
        </div>
      </div>

      {/* Calendar grid */}
      <div className="cal-grid">
        {DOW.map((d) => (
          <div key={d} className="cal-dow">{d}</div>
        ))}
        {cells.map((cell, i) => {
          const dayEntries = cell.dateStr ? byDate.get(cell.dateStr) ?? [] : [];
          const isToday = cell.dateStr === todayStr;
          return (
            <div key={i} className={`cal-day${cell.day === null ? " out" : ""}${isToday ? " today" : ""}`}>
              {cell.day !== null && <div className="dn">{cell.day}</div>}
              {dayEntries.map((e) => (
                <div
                  key={e.id}
                  className={`cal-event ${e.status}`}
                  title={`${e.title} · ${e.status}${e.last_error ? ` · ${e.last_error}` : ""}`}
                  onClick={() => onDelete(e)}
                >
                  <span className="ce-t">{timePart(e.scheduled_at)}</span>
                  <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{e.title}</div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <p className="meta">Tip: click a scheduled (not yet published) post to cancel it.</p>
    </div>
  );
}
