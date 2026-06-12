import Link from "next/link";

export default function QueuePage() {
  return (
    <div className="empty-soon">
      <h3>Auto-Queue — <span className="it">coming in v1.0</span></h3>
      <p>Set your weekly cadence once. The engine generates a month of posts per content pillar and auto-slots them into your best time windows. You just approve.</p>
      <br />
      <Link className="btn btn-red" href="/planner/ai">Preview the roadmap →</Link>
    </div>
  );
}
