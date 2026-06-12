"use client";

import { useRef, useState } from "react";

import { PF, useScheduler } from "@/lib/scheduler/context";
import {
  DOW, MONTHS, PLANNER_HOURS, dstr, fmtHour, startOfWeek, TODAY, type Post,
} from "@/lib/scheduler/data";

function PostCard({ post, top, onDragStart }: { post: Post; top: number; onDragStart: () => void }) {
  const { editPost } = useScheduler();
  const pf = PF[post.pf];
  return (
    <div
      className={`post-card ${pf.cls}`}
      draggable
      style={{ top, height: 78 }}
      onClick={(e) => { e.stopPropagation(); editPost(post.id); }}
      onDragStart={(e) => { onDragStart(); e.currentTarget.classList.add("dragging"); }}
      onDragEnd={(e) => e.currentTarget.classList.remove("dragging")}
    >
      <div className="pc-top">
        <span className="pc-ic" style={{ background: pf.bg }}>{pf.ic}</span>
        <span className="pc-time">{post.time}</span>
        <span className={`pc-status ${post.status}`} title={post.status} />
      </div>
      <div className="pc-text">{post.text}</div>
    </div>
  );
}

function WeekView() {
  const { visiblePosts, viewAnchor, quickAdd, movePost, showToast } = useScheduler();
  const dragId = useRef<number | null>(null);
  const [over, setOver] = useState<string | null>(null);

  const ws = startOfWeek(viewAnchor);
  const days = [...Array(7)].map((_, i) => {
    const d = new Date(ws);
    d.setDate(d.getDate() + i);
    return d;
  });
  const posts = visiblePosts();
  const todayStr = dstr(TODAY);

  const drop = (ds: string, hour: number) => {
    if (dragId.current == null) return;
    const time = String(hour).padStart(2, "0") + ":00";
    movePost(dragId.current, ds, time);
    const d = new Date(ds + "T00:00");
    showToast(`Post rescheduled to ${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)} · ${time}`);
    dragId.current = null;
    setOver(null);
  };

  return (
    <div className="cal-week">
      <div className="corner" />
      {days.map((d) => {
        const isToday = dstr(d) === todayStr;
        const cnt = posts.filter((p) => p.date === dstr(d)).length;
        return (
          <div key={dstr(d)} className={`day-head${isToday ? " is-today" : ""}`}>
            <div className="dow">{DOW[(d.getDay() + 6) % 7]}</div>
            <div className="dnum">{d.getDate()}</div>
            <div className="cnt">{cnt ? cnt + " posts" : "—"}</div>
          </div>
        );
      })}
      <div className="time-col">
        {PLANNER_HOURS.map((h) => <div key={h} className="time-slot">{fmtHour(h)}</div>)}
      </div>
      {days.map((d) => {
        const ds = dstr(d);
        return (
          <div key={ds} className="day-col">
            {PLANNER_HOURS.map((h) => {
              const key = `${ds}-${h}`;
              return (
                <div
                  key={h}
                  className={`hour-cell${over === key ? " over" : ""}`}
                  onClick={() => quickAdd(ds, String(h).padStart(2, "0") + ":00")}
                  onDragOver={(e) => { e.preventDefault(); setOver(key); }}
                  onDragLeave={() => setOver((o) => (o === key ? null : o))}
                  onDrop={(e) => { e.preventDefault(); drop(ds, h); }}
                />
              );
            })}
            {posts
              .filter((p) => p.date === ds)
              .map((p) => {
                const [hh, mm] = p.time.split(":").map(Number);
                if (hh < 7 || hh > 20) return null;
                const top = (hh - 7) * 88 + (mm / 60) * 88;
                return (
                  <PostCard key={p.id} post={p} top={top} onDragStart={() => { dragId.current = p.id; }} />
                );
              })}
          </div>
        );
      })}
    </div>
  );
}

function MonthView() {
  const { visiblePosts, viewAnchor, quickAdd, editPost } = useScheduler();
  const y = viewAnchor.getFullYear();
  const m = viewAnchor.getMonth();
  const first = new Date(y, m, 1);
  const startPad = (first.getDay() + 6) % 7;
  const gridStart = new Date(y, m, 1 - startPad);
  const posts = visiblePosts();
  const todayStr = dstr(TODAY);

  return (
    <div className="cal-month">
      {DOW.map((d) => <div key={d} className="mh">{d}</div>)}
      {[...Array(42)].map((_, i) => {
        const d = new Date(gridStart);
        d.setDate(d.getDate() + i);
        const ds = dstr(d);
        const out = d.getMonth() !== m;
        const isToday = ds === todayStr;
        const dayPosts = posts.filter((p) => p.date === ds).sort((a, b) => a.time.localeCompare(b.time));
        return (
          <div
            key={i}
            className={`m-cell${out ? " out" : ""}${isToday ? " today" : ""}`}
            onClick={() => quickAdd(ds, "10:00")}
          >
            <div className="mn">{d.getDate()}</div>
            {dayPosts.slice(0, 3).map((p) => (
              <div
                key={p.id}
                className={`m-chip ${PF[p.pf].cls}`}
                onClick={(e) => { e.stopPropagation(); editPost(p.id); }}
              >
                <span className="mt">{p.time}</span>
                <span className="mtxt">{p.text}</span>
              </div>
            ))}
            {dayPosts.length > 3 && <div className="m-more">+{dayPosts.length - 3} more</div>}
          </div>
        );
      })}
    </div>
  );
}

function ListView() {
  const { visiblePosts, editPost } = useScheduler();
  const sorted = [...visiblePosts()].sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));
  const todayStr = dstr(TODAY);

  if (!sorted.length) {
    return (
      <div className="list-view">
        <div className="empty-soon">
          <h3>No posts match</h3>
          <p>Adjust your channel filters or schedule a new post.</p>
        </div>
      </div>
    );
  }

  let lastDay = "";
  return (
    <div className="list-view">
      {sorted.map((p) => {
        const pf = PF[p.pf];
        const header = p.date !== lastDay;
        lastDay = p.date;
        const d = new Date(p.date + "T00:00");
        const label = p.date === todayStr ? "Today" : `${DOW[(d.getDay() + 6) % 7]}, ${d.getDate()} ${MONTHS[d.getMonth()]}`;
        return (
          <div key={p.id} style={{ display: "contents" }}>
            {header && <div className="list-day">{label}</div>}
            <div className="list-row" onClick={() => editPost(p.id)}>
              <div className="lt">{p.time}</div>
              <div className="lic" style={{ background: pf.bg }}>{pf.ic}</div>
              <div className="lbody">
                <div className="lx">{p.text}</div>
                <div className="lm">{pf.name}</div>
              </div>
              <div className={`lstatus ${p.status}`}>{p.status.toUpperCase()}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function PlannerCalendar() {
  const { view } = useScheduler();
  if (view === "week") return <WeekView />;
  if (view === "month") return <MonthView />;
  return <ListView />;
}
