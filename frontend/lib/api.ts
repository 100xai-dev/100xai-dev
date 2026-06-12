import { getBackendBaseUrl } from "@/lib/config";
import type { BlogJobOut, Persona } from "@/lib/types";
import type {
  ApproveBrandResponse,
  BillingSubscriptionResponse,
  BrandCreateRequest,
  BrandCreateResponse,
  BrandListResponse,
  BrandProfileContent,
  BrandProfileFull,
  BrandSummary,
  JobRead,
  PlanOut,
} from "@/lib/types";

// Minimal BrandData interface for scheduler persona
export interface BrandData {
  name: string;
  domain: string;
  url: string;
  one: string; // one-liner
  aud: string; // audience
  tone: string[]; // tone tags
  founder: string;
  role: string;
  mission: string;
  accent: string; // accent color
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  cache?: RequestCache;
};

function isServer(): boolean {
  return typeof window === "undefined";
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: HeadersInit = { "Content-Type": "application/json" };

  let url: string;
  if (isServer()) {
    url = `${getBackendBaseUrl()}${path}`;
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const token = cookieStore.get("100xai_access_token")?.value;
    if (token) headers.Authorization = `Bearer ${token}`;
  } else {
    url = `${getBackendBaseUrl()}${path}`;
    // Use getValidAccessToken so expired tokens are refreshed before the call
    const { getValidAccessToken } = await import("@/lib/auth");
    const token = await getValidAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: options.cache ?? "no-store",
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (payload.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch {
      // no-op: body may be empty (e.g. 404 from proxy)
    }
    throw new Error(detail);
  }
  // 204 No Content has no body — return null cast to T
  if (response.status === 204) return null as unknown as T;
  const text = await response.text();
  if (!text) return null as unknown as T;
  return JSON.parse(text) as T;
}

export async function listBrands(): Promise<BrandListResponse> {
  return apiRequest<BrandListResponse>("/v1/brands");
}

export async function getBrand(brandId: string): Promise<BrandSummary> {
  return apiRequest<BrandSummary>(`/v1/brands/${brandId}`);
}

export async function createBrand(payload: BrandCreateRequest): Promise<BrandCreateResponse> {
  return apiRequest<BrandCreateResponse>("/v1/brands", { method: "POST", body: payload });
}

export async function requestBrandDelete(brandId: string): Promise<void> {
  await apiRequest<void>(`/v1/brands/${brandId}`, { method: "DELETE" });
}

export async function getBrandProfile(brandId: string): Promise<BrandProfileFull> {
  return apiRequest<BrandProfileFull>(`/v1/brands/${brandId}/profile`);
}

export async function submitManualProfile(brandId: string, payload: BrandProfileContent): Promise<BrandProfileFull> {
  return apiRequest<BrandProfileFull>(`/v1/brands/${brandId}/profile`, {
    method: "POST",
    body: payload,
  });
}

export async function patchProfile(
  brandId: string,
  payload: Partial<BrandProfileFull>,
): Promise<BrandProfileFull> {
  return apiRequest<BrandProfileFull>(`/v1/brands/${brandId}/profile`, {
    method: "PATCH",
    body: payload,
  });
}

export async function approveBrand(brandId: string): Promise<ApproveBrandResponse> {
  return apiRequest<ApproveBrandResponse>(`/v1/brands/${brandId}/approve`, { method: "POST" });
}

export async function getJob(jobId: string): Promise<JobRead> {
  return apiRequest<JobRead>(`/v1/jobs/${jobId}`);
}

// Blog
export async function createBlogJob(
  brandId: string,
  keyword: string,
  includeImage: boolean = true,
): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs`, {
    method: "POST",
    body: { keyword, include_image: includeImage },
  });
}

export async function listBlogJobs(brandId: string): Promise<{ items: BlogJobOut[] }> {
  return apiRequest<{ items: BlogJobOut[] }>(`/v1/brands/${brandId}/blogs`);
}

export async function getBlogJob(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}`);
}

export async function approveBrief(brandId: string, jobId: string, selectedTitle?: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/approve-brief`, {
    method: "POST",
    body: { selected_title: selectedTitle ?? null },
  });
}

export async function rejectBrief(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/reject-brief`, { method: "POST" });
}

export async function approveArticle(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/approve-article`, { method: "POST" });
}

export async function rejectArticle(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/reject-article`, { method: "POST" });
}

export async function retryBlogJob(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/retry`, { method: "POST" });
}

// Keyword Research
export async function startKeywordResearch(brandId: string, seedKeyword: string): Promise<{
  job_id: string;
  brand_id: string;
  seed_keyword: string;
  status: string;
  message: string;
}> {
  return apiRequest(`/v1/brands/${brandId}/keywords/research`, {
    method: "POST",
    body: { seed_keyword: seedKeyword },
  });
}

export async function listKeywords(brandId: string, limit = 50, offset = 0): Promise<{
  keywords: Array<{
    id: string;
    related_keyword: string;
    primary_keyword: string;
    source_type: string;
    search_volume: number | null;
    keyword_difficulty: number | null;
    cpc: number | null;
    competition: number | null;
    search_intent: string | null;
    score: number | null;
    created_at: string;
  }>;
  total: number;
  brand_id: string;
  latest_job_id: string | null;
  research_status: string;
}> {
  return apiRequest(`/v1/brands/${brandId}/keywords?limit=${limit}&offset=${offset}`);
}

export async function getKeywordStats(brandId: string): Promise<{
  total_keywords: number;
  avg_search_volume: number | null;
  avg_difficulty: number | null;
  top_sources: Record<string, number>;
  completion_rate: number;
}> {
  return apiRequest(`/v1/brands/${brandId}/keywords/stats`);
}

// Billing
export async function listPlans(): Promise<{ plans: PlanOut[] }> {
  return apiRequest<{ plans: PlanOut[] }>("/v1/billing/plans");
}

export async function getSubscription(): Promise<BillingSubscriptionResponse> {
  return apiRequest<BillingSubscriptionResponse>("/v1/billing/subscription");
}

export async function subscribeToPlan(planCode: string): Promise<{
  subscription_id: string;
  key_id: string;
  plan_code: string;
}> {
  return apiRequest("/v1/billing/subscribe", { method: "POST", body: { plan_code: planCode } });
}

export async function cancelSubscription(): Promise<null> {
  return apiRequest("/v1/billing/cancel", { method: "POST" });
}

// SERP Analysis (Pipeline 2)
export async function startSerpAnalysis(brandId: string, keywords?: string[]): Promise<{
  job_id: string;
  brand_id: string;
  keywords_count: number;
  status: string;
  message: string;
}> {
  return apiRequest(`/v1/brands/${brandId}/serp-analysis`, {
    method: "POST",
    body: keywords ? { target_keywords: keywords } : {},
  });
}

export async function getSerpAnalysisResults(brandId: string): Promise<{
  serp_analyses: Array<{
    id: string;
    keyword_text: string;
    status: string;
    total_results_analyzed: number;
    avg_word_count: number | null;
    content_gap_score: number | null;
    created_at: string;
    competitors: Array<{
      url: string;
      title: string;
      content_strength: number | null;
      content_gaps: string[];
      competitive_advantage: string | null;
    }>;
  }>;
  total_analyses: number;
  latest_job_id: string | null;
  analysis_status: string;
}> {
  return apiRequest(`/v1/brands/${brandId}/serp-analysis`);
}

// BrandData (frontend) <-> Persona (backend) field mapping.
export function personaToBrandData(p: Persona): BrandData {
  return {
    name: p.name,
    domain: p.domain ?? "",
    url: p.url ?? "",
    one: p.one_liner,
    aud: p.audience,
    tone: p.tone_tags ?? [],
    founder: p.founder_name ?? "",
    role: p.founder_role ?? "",
    mission: p.mission ?? "",
    accent: p.accent_color ?? "#F58000",
  };
}

function brandDataToPayload(d: BrandData) {
  return {
    name: d.name,
    domain: d.domain || null,
    url: d.url || null,
    one_liner: d.one,
    audience: d.aud,
    tone_tags: d.tone,
    founder_name: d.founder || null,
    founder_role: d.role || null,
    mission: d.mission || null,
    accent_color: d.accent || null,
  };
}

export async function getPersona(brandId: string): Promise<Persona | null> {
  try {
    return await apiRequest<Persona>(`/v1/brands/${brandId}/persona`);
  } catch {
    return null; // 404 = not composed yet
  }
}

export async function savePersona(brandId: string, data: BrandData): Promise<Persona> {
  return apiRequest<Persona>(`/v1/brands/${brandId}/persona`, {
    method: "PUT",
    body: brandDataToPayload(data),
  });
}
