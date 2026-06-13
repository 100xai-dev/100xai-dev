// Renders a pipeline job's status as a coloured pill. Job statuses
// (QUEUED / NEW / RUNNING / SCHEDULED / COMPLETED / FAILED / CANCELLED) are
// distinct from BrandStatus, so this is intentionally separate from
// <StatusBadge>, which is typed for brand lifecycle states only.

type Tone = { color: string; bg: string; border: string };

const TONES: Record<string, Tone> = {
  success: { color: "var(--success)", bg: "var(--success-light)", border: "var(--success-border)" },
  danger: { color: "var(--danger)", bg: "var(--danger-light)", border: "var(--danger-border)" },
  accent: { color: "var(--accent)", bg: "var(--accent-light)", border: "var(--accent-border)" },
  info: { color: "var(--info)", bg: "var(--info-light)", border: "var(--info-border)" },
  muted: { color: "var(--text-secondary)", bg: "var(--bg-subtle)", border: "var(--border)" },
};

function toneFor(status: string): Tone {
  switch (status.toUpperCase()) {
    case "COMPLETED":
    case "SUCCEEDED":
    case "PUBLISHED":
      return TONES.success;
    case "FAILED":
      return TONES.danger;
    case "RUNNING":
    case "PROCESSING":
    case "GENERATING":
    case "WRITING":
      return TONES.accent;
    case "QUEUED":
    case "NEW":
    case "SCHEDULED":
    case "PENDING_REVIEW":
      return TONES.info;
    case "CANCELLED":
    case "REJECTED":
      return TONES.muted;
    default:
      return TONES.muted;
  }
}

function label(status: string): string {
  const s = status.trim();
  if (!s) return "Unknown";
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

export function JobStatusBadge({ status }: { status: string }) {
  const tone = toneFor(status);
  return (
    <span
      className="status-badge"
      style={{ color: tone.color, background: tone.bg, borderColor: tone.border }}
    >
      {label(status)}
    </span>
  );
}
