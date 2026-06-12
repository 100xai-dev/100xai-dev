// Brand-persona engine: derives a structured persona from the onboarding answers.
// Ported from the prototype's buildPersona(); returns data (not HTML) for JSX.

export interface BrandData {
  name: string;
  domain: string;
  url: string;
  one: string;
  aud: string;
  tone: string[];
  founder: string;
  role: string;
  mission: string;
  accent: string;
}

export const VOICE_MAP: Record<string, { h: string; p: string }> = {
  Bold: { h: "Bold & direct", p: "We lead with the point. No hedging, no filler — just the truth said plainly and early." },
  Warm: { h: "Warm & human", p: "We sound like a person who cares, not a brand performing. Empathy before pitch." },
  Authoritative: { h: "Authoritative", p: "We earn trust with specifics — names, numbers and proof, never adjectives alone." },
  Playful: { h: "Playful", p: "We keep it light where we can. A little wit makes the serious things land harder." },
  Inspiring: { h: "Inspiring", p: "We write to the bigger why — the change worth building toward, not just the feature." },
  Premium: { h: "Refined", p: "Every word is considered. Restraint is the luxury; we never shout to be heard." },
  Minimal: { h: "Spare & clear", p: "We cut until only the essential remains. Clarity is a form of respect." },
  Technical: { h: "Precise", p: "We respect the reader’s intelligence — accurate, concrete, and unafraid of depth." },
};

export const TONE_OPTIONS = [
  "Bold", "Warm", "Authoritative", "Playful",
  "Inspiring", "Premium", "Minimal", "Technical",
];

export const ACCENT_SWATCHES = ["#F58000", "#D9572F", "#1F3D2E", "#174F74", "#7A3CB5", "#C9A227"];

/* ---- colour helpers ---- */
function hx2rgb(h: string): [number, number, number] {
  let s = h.replace("#", "");
  if (s.length === 3) s = s.split("").map((x) => x + x).join("");
  return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
}
function rgb2hx(r: number, g: number, b: number): string {
  const c = (v: number) => ("0" + Math.max(0, Math.min(255, Math.round(v))).toString(16)).slice(-2);
  return "#" + c(r) + c(g) + c(b);
}
export function darken(h: string, p: number): string {
  const [r, g, b] = hx2rgb(h);
  return rgb2hx(r * (1 - p), g * (1 - p), b * (1 - p));
}
export function lighten(h: string, p: number): string {
  const [r, g, b] = hx2rgb(h);
  return rgb2hx(r + (255 - r) * p, g + (255 - g) * p, b + (255 - b) * p);
}
export function rgbaC(h: string, a: number): string {
  const [r, g, b] = hx2rgb(h);
  return `rgba(${r},${g},${b},${a})`;
}

function joinList(a: string[]): string {
  const l = a.map((x) => x.toLowerCase());
  if (l.length === 0) return "considered";
  if (l.length === 1) return l[0];
  if (l.length === 2) return l[0] + " and " + l[1];
  return l.slice(0, -1).join(", ") + " and " + l[l.length - 1];
}
export function shortText(s: string, n: number): string {
  const w = s.split(/\s+/);
  return w.length <= n ? s : w.slice(0, n).join(" ") + "…";
}

export function cleanDomain(u: string): string {
  return u.trim().replace(/^https?:\/\//i, "").replace(/^www\./i, "").replace(/\/+$/, "").split("/")[0];
}

export function isValidDomain(dom: string): boolean {
  return /^[a-z0-9-]+(\.[a-z0-9-]+)+$/i.test(dom);
}

export interface PersonaCard { ix: string; h: string; p: string }
export interface PersonaSwatch { n: string; hx: string; c: string }
export interface PersonaVoice { vn: string; h: string; p: string }

export interface Persona {
  d: BrandData;
  accent: string;
  accent2: string;
  tint: string;
  initial: string;
  titleWords: { lead: string; last: string };
  toneAdj: string;
  voiceLabel: string;
  palette: PersonaSwatch[];
  voiceCards: PersonaVoice[];
  believe: PersonaCard[];
  values: PersonaCard[];
  year: number;
}

export function buildPersona(d: BrandData): Persona {
  const accent = d.accent;
  const accent2 = darken(accent, 0.2);
  const tint = rgbaC(accent, 0.08);
  const tintHex = lighten(accent, 0.9);
  const initial = (d.name.trim()[0] || "B").toUpperCase();

  const nameWords = d.name.trim().split(/\s+/);
  const titleWords = nameWords.length > 1
    ? { lead: nameWords.slice(0, -1).join(" "), last: nameWords.slice(-1)[0] }
    : { lead: "", last: d.name };

  const toneAdj = joinList(d.tone);
  const voiceList = (d.tone.length ? d.tone : ["Bold", "Warm", "Authoritative", "Inspiring"]).slice(0, 4);
  const voiceCards: PersonaVoice[] = voiceList.map((t, idx) => {
    const v = VOICE_MAP[t] || { h: t, p: "A defining quality of how the brand sounds." };
    return { vn: "0" + (idx + 1), h: v.h, p: v.p };
  });

  const palette: PersonaSwatch[] = [
    { n: "Brand", hx: accent, c: accent },
    { n: "Brand Deep", hx: accent2, c: accent2 },
    { n: "Soft Tint", hx: tintHex, c: tintHex },
    { n: "Ink Navy", hx: "#0C1124", c: "#0C1124" },
    { n: "Field Cream", hx: "#FAFAF7", c: "#FAFAF7" },
  ];

  const audShort = shortText(d.aud, 9);
  const believe: PersonaCard[] = [
    { ix: "i.", h: "Trust is the product", p: `Before a single member of ${audShort} chooses ${d.name}, they decide whether to believe us. Everything we ship protects that decision.` },
    { ix: "ii.", h: "Show, don’t claim", p: "We lead with proof — the work itself, real names, real numbers. Adjectives are cheap; evidence compounds over time." },
    { ix: "iii.", h: "Built with, not at", p: `${d.name} is shaped alongside the people it serves. Their reality is the brief — never an afterthought once the product ships.` },
  ];

  const values: PersonaCard[] = [
    { ix: "i.", h: "Clarity", p: "Say the true thing, plainly. Confusion is a cost we refuse to pass to the people we serve." },
    { ix: "ii.", h: "Integrity", p: "We keep the promise even when no one is watching the dashboard. The standard is the standard." },
    { ix: "iii.", h: "Craft", p: "Details are not decoration — they are the difference between fine and unforgettable." },
    { ix: "iv.", h: "Momentum", p: "We move. Shipped-and-improving beats perfect-and-theoretical, every single week." },
    { ix: "v.", h: "Community", p: "The network is the moat. We grow by making the people around us succeed first." },
    { ix: "vi.", h: "Ambition", p: `We measure ourselves against the mission — ${shortText(d.mission, 10)} — not against the competition.` },
  ];

  return {
    d, accent, accent2, tint, initial, titleWords, toneAdj,
    voiceLabel: d.tone.length ? d.tone.join(" · ") : "Considered",
    palette, voiceCards, believe, values,
    year: new Date().getFullYear(),
  };
}

export const DEFAULT_BRAND: BrandData = {
  name: "Roadveer",
  domain: "roadveer.com",
  url: "https://roadveer.com",
  one: "India's on-demand highway assistance & driver-welfare network",
  aud: "Truck drivers, fleet owners and highway responders across India",
  tone: ["Bold", "Warm", "Inspiring"],
  founder: "Farukh Yelapure",
  role: "Founder & CEO",
  mission: "a Zero-Accident Bharat — making every Indian highway safer, one verified dispatch at a time",
  accent: "#F58000",
};
