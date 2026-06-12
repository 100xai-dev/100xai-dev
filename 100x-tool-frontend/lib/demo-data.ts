// Demo-mode fixtures for the pipeline pages. Active only when
// NEXT_PUBLIC_DEMO_MODE === "true". Lets the whole pipeline/output UI render and
// be clicked through without a live backend. None of this is used in production.
//
// Shapes mirror the real backend responses (KeywordOut, SerpAnalysisItem,
// BlogDraftOut, JobRead) so the demo path and the live path share components.

import type {
  BlogDraftOut,
  BrandSummary,
  JobRead,
  KeywordOut,
  SerpAnalysisItem,
} from "@/lib/types";

const DEMO_BRAND_NAMES: Record<string, string> = {
  "mock-brand-1": "Aether Dynamics",
  "mock-brand-2": "Sola Biosystems",
  "mock-brand-3": "Vesper Heavy Industries",
  "mock-brand-4": "Chronos AI Labs",
};

const now = Date.parse("2026-06-02T10:00:00Z");
const iso = (offsetMin: number) => new Date(now + offsetMin * 60_000).toISOString();

export function demoBrand(brandId: string): BrandSummary {
  return {
    id: brandId,
    name: DEMO_BRAND_NAMES[brandId] ?? "Demo Brand",
    website_url: "https://demo-brand.example.com",
    dna_source: "crawl",
    status: "READY",
    failure_reason: null,
    created_by: "00000000-0000-0000-0000-000000000001",
    created_at: iso(-2880),
    updated_at: iso(-60),
    channel_readiness: {},
    active_job: null,
  };
}

export const DEMO_COMPLETED_JOB = "demo-job-completed";
export const DEMO_RUNNING_JOB = "demo-job-running";
export const DEMO_FAILED_JOB = "demo-job-failed";

function baseJob(brandId: string): Omit<JobRead, "id" | "status" | "stage" | "started_at" | "finished_at" | "error_message"> {
  return {
    org_id: "00000000-0000-0000-0000-000000000001",
    brand_id: brandId,
    job_type: "keyword_research",
    progress: {},
    attempt_count: 1,
    max_attempts: 3,
  };
}

export function demoBrandJobs(brandId: string): JobRead[] {
  return [
    {
      ...baseJob(brandId),
      id: DEMO_COMPLETED_JOB,
      job_type: "content_generation",
      status: "SUCCEEDED",
      stage: "COMPLETE",
      started_at: iso(0),
      finished_at: iso(42),
      error_message: null,
    },
    {
      ...baseJob(brandId),
      id: DEMO_RUNNING_JOB,
      status: "RUNNING",
      stage: "KEYWORD",
      started_at: iso(120),
      finished_at: null,
      error_message: null,
    },
    {
      ...baseJob(brandId),
      id: DEMO_FAILED_JOB,
      job_type: "serp_analysis",
      status: "FAILED",
      stage: "SERP",
      started_at: iso(-1440),
      finished_at: iso(-1430),
      error_message: "SERP provider returned 429 (rate limited) after 3 attempts.",
    },
  ];
}

export function demoJob(brandId: string, jobId: string): JobRead {
  const match = demoBrandJobs(brandId).find((j) => j.id === jobId);
  if (match) return match;
  // Unknown id (e.g. an active_job link from the brand detail mock) → show the
  // fully-populated completed job so the demo always renders something useful.
  return { ...demoBrandJobs(brandId)[0], id: jobId };
}

// [related_keyword, source_type, search_volume, keyword_difficulty, cpc, score]
const KEYWORD_ROWS: Array<[string, string, number, number, number, number]> = [
  ["project management software", "primary_search", 49500, 78, 12.4, 0.42],
  ["best project management tools", "serp_suggestions", 22200, 64, 9.8, 0.71],
  ["free project management software", "serp_suggestions", 18100, 52, 4.2, 0.83],
  ["agile project management", "dataforseo_ideas", 14800, 58, 6.1, 0.66],
  ["project management for small teams", "sub_topics", 2400, 31, 3.4, 0.88],
  ["kanban board software", "serp_autocomplete", 9900, 47, 5.7, 0.62],
  ["gantt chart tool", "serp_autocomplete", 8100, 44, 5.1, 0.59],
  ["task tracking app", "dataforseo_suggestions", 6600, 39, 4.0, 0.55],
  ["project management software for startups", "sub_topics", 1300, 27, 3.9, 0.91],
  ["enterprise project management platform", "dataforseo_ideas", 3200, 71, 14.2, 0.34],
  ["project management methodologies", "serp_suggestions", 12100, 35, 2.1, 0.48],
  ["scrum vs kanban", "serp_suggestions", 5400, 29, 1.8, 0.27],
];

export function demoKeywords(brandId: string, jobId: string): KeywordOut[] {
  return KEYWORD_ROWS.map(([kw, source, volume, difficulty, cpc, score], i) => ({
    id: `demo-kw-${i}`,
    related_keyword: kw,
    primary_keyword: "project management software",
    source_type: source,
    search_volume: volume,
    keyword_difficulty: difficulty,
    cpc,
    competition: Math.round((difficulty / 100) * 100) / 100,
    search_intent: i % 3 === 0 ? "informational" : "commercial",
    score,
    created_at: iso(10),
  }));
}

export function demoSerp(brandId: string, jobId: string): SerpAnalysisItem[] {
  return [
    {
      id: "demo-serp-0",
      keyword_text: "best project management tools",
      status: "COMPLETED",
      total_results_analyzed: 3,
      avg_word_count: 3530,
      content_gap_score: 0.4,
      created_at: iso(20),
      competitors: [
        {
          url: "https://www.competitor-a.com/blog/best-pm-tools",
          title: "21 Best Project Management Tools in 2026",
          content_strength: 0.82,
          content_gaps: ["pricing transparency", "small-team use cases"],
          competitive_advantage: "Comprehensive comparison table, strong on-page SEO, fast load.",
        },
        {
          url: "https://www.competitor-b.io/resources/pm-software",
          title: "Project Management Software: The Complete Guide",
          content_strength: 0.74,
          content_gaps: ["comparison table", "internal linking"],
          competitive_advantage: "Deep methodology section, embedded video walkthroughs.",
        },
        {
          url: "https://reviews.competitor-c.com/pm",
          title: "We Tested 30 PM Tools — Here Are the Winners",
          content_strength: 0.68,
          content_gaps: ["AI-assisted features", "2026 examples"],
          competitive_advantage: "Original testing data, screenshots, trust signals.",
        },
      ],
    },
    {
      id: "demo-serp-1",
      keyword_text: "free project management software",
      status: "COMPLETED",
      total_results_analyzed: 2,
      avg_word_count: 2050,
      content_gap_score: 0.3,
      created_at: iso(22),
      competitors: [
        {
          url: "https://www.competitor-d.com/free-pm",
          title: "9 Genuinely Free Project Management Tools",
          content_strength: 0.7,
          content_gaps: ["seat limits", "hidden caps"],
          competitive_advantage: "Clear free-vs-paid breakdown, good UX screenshots.",
        },
        {
          url: "https://blog.competitor-e.com/free-tools-2026",
          title: "The Best Free PM Software (No Credit Card)",
          content_strength: 0.55,
          content_gaps: ["original analysis"],
          competitive_advantage: "Strong CTA placement, comparison filters.",
        },
      ],
    },
  ];
}

const DEMO_ARTICLE_HTML = `
<h1>The Best Project Management Software for Small Teams in 2026</h1>
<p>Choosing the right project management tool can be the difference between a team that ships predictably and one that drowns in status updates. In this guide we break down the options that actually work for teams of 5–20 people — without enterprise bloat or surprise per-seat pricing.</p>
<h2>What small teams actually need</h2>
<p>Bigger isn't better. The features that matter most for lean teams are a fast inbox-zero task view, lightweight planning, and pricing that doesn't punish you for adding a contractor for a month.</p>
<ul>
  <li><strong>A single source of truth</strong> — tasks, docs, and deadlines in one place.</li>
  <li><strong>Flexible views</strong> — board, list, and timeline without paying extra.</li>
  <li><strong>Transparent pricing</strong> — flat tiers, generous free plans, no hidden seat caps.</li>
</ul>
<h2>Our top picks</h2>
<h3>1. Best overall for small teams</h3>
<p>A balanced tool that nails the basics: quick capture, clear ownership, and a board that doesn't need a manual.</p>
<h2>How we evaluated</h2>
<p>We scored each tool on setup time, day-to-day speed, pricing transparency, and how well it serves a team that can't afford a dedicated admin.</p>
<p>Ready to ship more predictably? <a href="#">Start with the free plan</a> and upgrade only when your team outgrows it.</p>
`;

export function demoDraft(jobId: string): BlogDraftOut {
  return {
    id: "demo-draft-1",
    job_id: jobId,
    title: "The Best Project Management Software for Small Teams in 2026",
    meta_description:
      "A practical, no-bloat guide to the best project management software for small teams in 2026 — with transparent pricing and real small-team use cases.",
    html_content: DEMO_ARTICLE_HTML,
    word_count: 2450,
    seo_score: 86,
    aeo_score: 78,
    virality_score: 64,
    featured_image_url: "https://picsum.photos/seed/100xai-pm/1200/480",
    approved: false,
    created_at: iso(40),
  };
}
