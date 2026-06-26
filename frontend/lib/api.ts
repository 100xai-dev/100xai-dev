import { getBackendBaseUrl } from "@/lib/config";
import type {
  AccessTokenResponse,
  AddSourceRequest,
  AddSourceResponse,
  ApproveBrandResponse,
  ApproveBriefRequest,
  AuthResponse,
  BillingSubscriptionResponse,
  BlogJobCreate,
  BlogJobListResponse,
  BlogJobOut,
  BrandCreateRequest,
  BrandCreateResponse,
  BrandListResponse,
  BrandProfileContent,
  BrandProfileFull,
  BrandProfilePatch,
  BrandSourceListResponse,
  BrandSummary,
  BulkScheduleRequest,
  BulkScheduleResponse,
  CalendarEntry,
  ChannelIntegration,
  ContentGenerationRequest,
  ContentGenerationResponse,
  DeleteBrandResponse,
  IntegrationListResponse,
  IntegrationTestResponse,
  JobRead,
  KeywordListResponse,
  KeywordResearchRequest,
  KeywordResearchResponse,
  KeywordStatsResponse,
  LoginRequest,
  MeResponse,
  PipelineStatusResponse,
  PlanOut,
  PublishingStatsResponse,
  ReingestResponse,
  ScheduleRead,
  SerpAnalysisResponse,
  SerpAnalysisStartResponse,
  SignupRequest,
  WordPressSetupRequest,
  WordPressTestRequest,
  OrgListResponse,
  CreateOrgRequest,
  CreateOrgResponse,
  UpdateOrgRequest,
  OrgUserListResponse,
  OrgUserOut,
  CreateOrgUserRequest,
  UpdateOrgUserRequest,
} from "@/lib/types";

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  cache?: RequestCache;
};

/**
 * Error thrown by {@link apiRequest} that preserves the HTTP status and any
 * machine-readable `code` from the backend's `{detail: {code, message}}` body
 * (e.g. `subscription_required`, `plan_limit_reached`), so callers can branch
 * on it instead of string-matching the message.
 */
export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function isServer(): boolean {
  return typeof window === "undefined";
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  // Server components hit the backend directly with the server-only token.
  // Client components hit the same-origin Next route-handler proxy, which
  // injects the token server-side so it never reaches the browser.
  const url = isServer() ? `${getBackendBaseUrl()}${path}` : `/api${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (isServer()) {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const token = cookieStore.get("100xai_access_token")?.value;
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const actingOrg = cookieStore.get("100xai_acting_org")?.value;
    if (actingOrg) {
      headers["X-Acting-Org-Id"] = actingOrg;
    }
  } else {
    const match = document.cookie.match(/(?:^|;\s*)100xai_acting_org=([^;]+)/);
    if (match) {
      headers["X-Acting-Org-Id"] = decodeURIComponent(match[1]);
    }
  }
  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: options.cache ?? "no-store",
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    let code: string | undefined;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (payload.detail && typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (payload.detail && typeof payload.detail === "object") {
        const obj = payload.detail as { code?: string; message?: string };
        code = obj.code;
        detail = obj.message ?? JSON.stringify(payload.detail);
      }
    } catch {
      // no-op fallback to status text
    }
    throw new ApiError(detail, response.status, code);
  }
  // 204 No Content (logout) — nothing to parse.
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth — /v1/auth
// ─────────────────────────────────────────────────────────────────────────────
export function signup(payload: SignupRequest): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/v1/auth/signup", { method: "POST", body: payload });
}

export function login(payload: LoginRequest): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/v1/auth/login", { method: "POST", body: payload });
}

export function refreshAccessToken(refresh_token: string): Promise<AccessTokenResponse> {
  return apiRequest<AccessTokenResponse>("/v1/auth/refresh", { method: "POST", body: { refresh_token } });
}

export function logout(refresh_token: string): Promise<void> {
  return apiRequest<void>("/v1/auth/logout", { method: "POST", body: { refresh_token } });
}

export function getMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>("/v1/auth/me");
}

// ─────────────────────────────────────────────────────────────────────────────
// Brands — /v1/brands
// ─────────────────────────────────────────────────────────────────────────────
export function listBrands(): Promise<BrandListResponse> {
  return apiRequest<BrandListResponse>("/v1/brands");
}

export function getBrand(brandId: string): Promise<BrandSummary> {
  return apiRequest<BrandSummary>(`/v1/brands/${brandId}`);
}

export function createBrand(payload: BrandCreateRequest): Promise<BrandCreateResponse> {
  return apiRequest<BrandCreateResponse>("/v1/brands", { method: "POST", body: payload });
}

export function deleteBrand(brandId: string): Promise<DeleteBrandResponse> {
  return apiRequest<DeleteBrandResponse>(`/v1/brands/${brandId}`, { method: "DELETE" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Brand DNA profile — /v1/brands/{id}/profile + /approve
// ─────────────────────────────────────────────────────────────────────────────
export function getBrandProfile(brandId: string): Promise<BrandProfileFull> {
  return apiRequest<BrandProfileFull>(`/v1/brands/${brandId}/profile`);
}

export function submitManualProfile(brandId: string, payload: BrandProfileContent): Promise<BrandProfileFull> {
  return apiRequest<BrandProfileFull>(`/v1/brands/${brandId}/profile`, { method: "POST", body: payload });
}

export function patchProfile(brandId: string, payload: BrandProfilePatch): Promise<BrandProfileFull> {
  return apiRequest<BrandProfileFull>(`/v1/brands/${brandId}/profile`, { method: "PATCH", body: payload });
}

export function approveBrand(brandId: string): Promise<ApproveBrandResponse> {
  return apiRequest<ApproveBrandResponse>(`/v1/brands/${brandId}/approve`, { method: "POST" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Jobs — /v1/jobs/{id} (single job poll; there is no list endpoint)
// ─────────────────────────────────────────────────────────────────────────────
export function getJob(jobId: string): Promise<JobRead> {
  return apiRequest<JobRead>(`/v1/jobs/${jobId}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Pipeline 1 — Keyword research (brand-scoped)
// ─────────────────────────────────────────────────────────────────────────────
export function startKeywordResearch(
  brandId: string,
  payload: KeywordResearchRequest,
): Promise<KeywordResearchResponse> {
  return apiRequest<KeywordResearchResponse>(`/v1/brands/${brandId}/keywords/research`, {
    method: "POST",
    body: payload,
  });
}

export function listKeywords(brandId: string, limit = 50, offset = 0): Promise<KeywordListResponse> {
  return apiRequest<KeywordListResponse>(`/v1/brands/${brandId}/keywords?limit=${limit}&offset=${offset}`);
}

export function getKeywordStats(brandId: string): Promise<KeywordStatsResponse> {
  return apiRequest<KeywordStatsResponse>(`/v1/brands/${brandId}/keywords/stats`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Pipeline 2 — SERP analysis (brand-scoped)
// ─────────────────────────────────────────────────────────────────────────────
export function startSerpAnalysis(brandId: string): Promise<SerpAnalysisStartResponse> {
  return apiRequest<SerpAnalysisStartResponse>(`/v1/brands/${brandId}/serp-analysis`, {
    method: "POST",
    body: {},
  });
}

export function getSerpAnalysis(brandId: string): Promise<SerpAnalysisResponse> {
  return apiRequest<SerpAnalysisResponse>(`/v1/brands/${brandId}/serp-analysis`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Pipeline 3 — Content generation + pipeline status (brand-scoped)
// ─────────────────────────────────────────────────────────────────────────────
export function startContentGeneration(
  brandId: string,
  payload: ContentGenerationRequest,
): Promise<ContentGenerationResponse> {
  return apiRequest<ContentGenerationResponse>(`/v1/brands/${brandId}/content-generation`, {
    method: "POST",
    body: payload,
  });
}

export function getPipelineStatus(brandId: string): Promise<PipelineStatusResponse> {
  return apiRequest<PipelineStatusResponse>(`/v1/brands/${brandId}/pipeline-status`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Blogs (content review) — /v1/brands/{id}/blogs
// ─────────────────────────────────────────────────────────────────────────────
export function createBlogJob(brandId: string, payload: BlogJobCreate): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs`, { method: "POST", body: payload });
}

export function listBlogJobs(brandId: string): Promise<BlogJobListResponse> {
  return apiRequest<BlogJobListResponse>(`/v1/brands/${brandId}/blogs`);
}

export function getBlogJob(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}`);
}

export function approveArticle(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/approve-article`, { method: "POST" });
}

export function rejectArticle(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/reject-article`, { method: "POST" });
}

export function retryBlogJob(brandId: string, jobId: string): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/retry`, { method: "POST" });
}

export function approveBrief(brandId: string, jobId: string, payload: ApproveBriefRequest = {}): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs/${jobId}/approve-brief`, {
    method: "POST",
    body: payload,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Brand knowledge sources — /v1/brands/{id}/sources
// ─────────────────────────────────────────────────────────────────────────────
export function listBrandSources(brandId: string): Promise<BrandSourceListResponse> {
  return apiRequest<BrandSourceListResponse>(`/v1/brands/${brandId}/sources`);
}

export function addBrandSource(brandId: string, payload: AddSourceRequest): Promise<AddSourceResponse> {
  return apiRequest<AddSourceResponse>(`/v1/brands/${brandId}/sources`, { method: "POST", body: payload });
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

export function reingestSources(brandId: string): Promise<ReingestResponse> {
  return apiRequest<ReingestResponse>(`/v1/brands/${brandId}/sources/reingest`, { method: "POST" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Integrations — /v1/brands/{id}/integrations
// ─────────────────────────────────────────────────────────────────────────────
export function listIntegrations(brandId: string): Promise<IntegrationListResponse> {
  return apiRequest<IntegrationListResponse>(`/v1/brands/${brandId}/integrations`);
}

export function listChannelIntegrations(brandId: string): Promise<ChannelIntegration[]> {
  return apiRequest<ChannelIntegration[]>(`/v1/brands/${brandId}/integrations?format=channel`);
}

export function setupWordPress(
  brandId: string,
  payload: WordPressSetupRequest,
): Promise<{ integration_account_id: string; status: string; tested_at: string; site_info: Record<string, unknown> }> {
  return apiRequest(`/v1/brands/${brandId}/integrations/wordpress`, { method: "POST", body: payload });
}

export function testWordPress(brandId: string, payload: WordPressTestRequest): Promise<IntegrationTestResponse> {
  return apiRequest<IntegrationTestResponse>(`/v1/brands/${brandId}/integrations/wordpress/test`, {
    method: "POST",
    body: payload,
  });
}

export function testIntegration(brandId: string, providerOrId: string): Promise<IntegrationTestResponse> {
  return apiRequest<IntegrationTestResponse>(`/v1/brands/${brandId}/integrations/${providerOrId}/test`, {
    method: "POST",
  });
}

export function removeIntegration(brandId: string, provider: string): Promise<void> {
  return apiRequest<void>(`/v1/brands/${brandId}/integrations/${provider}`, { method: "DELETE" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Schedules — /v1/schedules
// ─────────────────────────────────────────────────────────────────────────────
export function createSchedulesBulk(brandId: string, payload: BulkScheduleRequest): Promise<BulkScheduleResponse> {
  return apiRequest<BulkScheduleResponse>(`/v1/schedules/brands/${brandId}/bulk`, {
    method: "POST",
    body: payload,
  });
}

export function getBrandCalendar(brandId: string, year: number, month: number): Promise<CalendarEntry[]> {
  return apiRequest<CalendarEntry[]>(`/v1/schedules/brands/${brandId}/calendar?year=${year}&month=${month}`);
}

export function getSchedule(scheduleId: string): Promise<ScheduleRead> {
  return apiRequest<ScheduleRead>(`/v1/schedules/${scheduleId}`);
}

export function deleteSchedule(scheduleId: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/v1/schedules/${scheduleId}`, { method: "DELETE" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Publishing monitoring — /v1/publishing
// ─────────────────────────────────────────────────────────────────────────────
export function getPublishingStats(brandId: string, days = 30): Promise<PublishingStatsResponse> {
  return apiRequest<PublishingStatsResponse>(`/v1/publishing/stats?brand_id=${brandId}&days=${days}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Superadmin — /v1/superadmin
// ─────────────────────────────────────────────────────────────────────────────
export function listOrganizations(): Promise<OrgListResponse> {
  return apiRequest<OrgListResponse>("/v1/superadmin/orgs");
}

export function createOrganization(payload: CreateOrgRequest): Promise<CreateOrgResponse> {
  return apiRequest<CreateOrgResponse>("/v1/superadmin/orgs", { method: "POST", body: payload });
}

export function updateOrganization(orgId: string, payload: UpdateOrgRequest): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}`, { method: "PATCH", body: payload });
}

export function suspendOrganization(orgId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/suspend`, { method: "POST" });
}

export function unsuspendOrganization(orgId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/unsuspend`, { method: "POST" });
}

export function deleteOrganization(orgId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}`, { method: "DELETE" });
}

export function enterOrganization(orgId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/enter`, { method: "POST" });
}

export function listOrgUsers(orgId: string): Promise<OrgUserListResponse> {
  return apiRequest<OrgUserListResponse>(`/v1/superadmin/orgs/${orgId}/users`);
}

export function createOrgUser(orgId: string, payload: CreateOrgUserRequest): Promise<OrgUserOut> {
  return apiRequest<OrgUserOut>(`/v1/superadmin/orgs/${orgId}/users`, { method: "POST", body: payload });
}

export function updateOrgUser(orgId: string, userId: string, payload: UpdateOrgUserRequest): Promise<OrgUserOut> {
  return apiRequest<OrgUserOut>(`/v1/superadmin/orgs/${orgId}/users/${userId}`, { method: "PATCH", body: payload });
}

export function deleteOrgUser(orgId: string, userId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/users/${userId}`, { method: "DELETE" });
}

export function resetOrgUserPassword(orgId: string, userId: string): Promise<unknown> {
  return apiRequest(`/v1/superadmin/orgs/${orgId}/users/${userId}/reset-password`, { method: "POST" });
}
