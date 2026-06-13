// Static demo data + helpers for the Schedulr planner.
// Ported from the standalone prototype; swap for real API later.

export type PlatformKey = "blog" | "li" | "ig";
export type PostStatus = "scheduled" | "draft" | "ai";

export interface Platform {
  key: PlatformKey;
  cls: string;
  ic: string;
  name: string;
  bg: string;
}

export interface Post {
  id: number;
  pf: PlatformKey;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
  status: PostStatus;
  text: string;
}

export const PF: Record<PlatformKey, Platform> = {
  blog: { key: "blog", cls: "blog", ic: "B", name: "Blog", bg: "var(--blog)" },
  li: { key: "li", cls: "li", ic: "in", name: "LinkedIn", bg: "var(--li)" },
  ig: { key: "ig", cls: "ig", ic: "ig", name: "Instagram", bg: "var(--ig)" },
};

export const PLATFORM_ORDER: PlatformKey[] = ["blog", "li", "ig"];

// Fixed demo "today" so the seeded calendar always lines up.
export const TODAY = new Date(2026, 5, 7);

export const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
export const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// Local-time YYYY-MM-DD (avoids UTC off-by-one from toISOString).
export function dstr(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function offsetDate(days: number): string {
  const d = new Date(TODAY);
  d.setDate(d.getDate() + days);
  return dstr(d);
}

export function startOfWeek(d: Date): Date {
  const x = new Date(d);
  const day = (x.getDay() + 6) % 7;
  x.setDate(x.getDate() - day);
  x.setHours(0, 0, 0, 0);
  return x;
}

export function fmtHour(h: number): string {
  const am = h < 12 ? "am" : "pm";
  let hh = h % 12;
  if (hh === 0) hh = 12;
  return hh + " " + am;
}

export const PLANNER_HOURS = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

export const SEED_POSTS: Post[] = [
  { id: 1, pf: "li", date: offsetDate(0), time: "09:30", status: "scheduled", text: "Driver Dignity is infrastructure, not charity. 240 new Rakshak enrollments this week on the Maharashtra corridor." },
  { id: 2, pf: "blog", date: offsetDate(0), time: "11:00", status: "scheduled", text: "New blog: How highway welfare programs reduce driver turnover by 38% — the Roadveer model explained." },
  { id: 3, pf: "ig", date: offsetDate(0), time: "18:00", status: "draft", text: "Behind the wheel: a day with our Highway Help crew near Pune. Reel drops tonight." },
  { id: 4, pf: "li", date: offsetDate(1), time: "10:00", status: "scheduled", text: "Vendor Growth spotlight: how a roadside dhaba doubled revenue after joining the Roadveer network." },
  { id: 5, pf: "ig", date: offsetDate(1), time: "14:00", status: "ai", text: "AI-drafted: 5 things every long-haul driver carries. Carousel ready for review." },
  { id: 6, pf: "blog", date: offsetDate(2), time: "09:00", status: "ai", text: "AI-generated draft: \"Maharashtra Mission — building India's first driver-first highway economy.\"" },
  { id: 7, pf: "li", date: offsetDate(2), time: "16:00", status: "scheduled", text: "Founder note from Farukh Yelapure on why dignity scales better than discounts." },
  { id: 8, pf: "ig", date: offsetDate(3), time: "12:00", status: "draft", text: "Rakshak enrollment camp — Nashik. Swipe to see the turnout." },
  { id: 9, pf: "blog", date: offsetDate(4), time: "10:30", status: "scheduled", text: "Weekly digest: Highway Help responses, vendor onboarding & welfare wins." },
  { id: 10, pf: "li", date: offsetDate(4), time: "15:00", status: "scheduled", text: "We are hiring corridor coordinators across 4 districts. Driver-first leaders, apply within." },
  { id: 11, pf: "ig", date: offsetDate(5), time: "11:00", status: "scheduled", text: "Sunday stories from the road. Tag a driver who keeps India moving." },
  { id: 12, pf: "li", date: offsetDate(-1), time: "10:00", status: "scheduled", text: "Recap: last week we crossed 5,000 enrolled drivers. Thank you to every coordinator." },
  { id: 13, pf: "blog", date: offsetDate(7), time: "09:00", status: "ai", text: "AI queued: \"The economics of treating drivers like partners.\"" },
  { id: 14, pf: "ig", date: offsetDate(8), time: "17:30", status: "draft", text: "Throwback to the first Rakshak camp. Look how far the movement has come." },
  { id: 15, pf: "li", date: offsetDate(10), time: "10:00", status: "scheduled", text: "Maharashtra Mission update — corridor 3 now fully live." },
];
