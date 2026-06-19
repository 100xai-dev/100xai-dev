// Hand-mirrored from the backend Pydantic schemas (backend/app/schemas/*, models/*).
// The backend is the source of truth — every type here maps to a real endpoint
// response. Do NOT invent fields the API does not return.

// ─────────────────────────────────────────────────────────────────────────────
// Auth — backend/app/schemas/auth.py
// ─────────────────────────────────────────────────────────────────────────────
export interface SignupRequest {
  name: string;
  email: string;
  password: string;
  organization_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface UserOut {
  id: string;
  name: string | null;
  email: string;
  role: string;
  org_id: string;
  email_verified: boolean;
}

export interface OrgOut {
  id: string;
  name: string;
  plan_code: string;
}

export interface AuthResponse {
  user: UserOut;
  organization: OrgOut;
  access_token: string;
  refresh_token: string;
  terms_acceptance_required: boolean;
  terms_current_version: string | null;
}

export type SignupResponse = {
  user: UserOut;
  organization: OrgOut;
  requires_verification: boolean;
};

export interface AccessTokenResponse {
  access_token: string;
}

export interface MeResponse {
  user: UserOut;
  organization: OrgOut;
}

export interface PlanOut {
  code: string;
  name: string;
  price_inr: number;
  limits: Record<string, number>;
  subscribable: boolean;
}

export interface SubscriptionOut {
  status: string;
  plan_code: string;
  razorpay_subscription_id: string | null;
  current_period_end: string | null;
}

export interface BillingSubscriptionResponse {
  plan_code: string;
  plan_name: string;
  limits: Record<string, number>;
  subscription: SubscriptionOut | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Brands — backend/app/schemas/brand.py
// ─────────────────────────────────────────────────────────────────────────────
export type DnaSource = "crawl" | "manual";

export type BrandStatus =
  | "DRAFT"
  | "CRAWLING"
  | "EXTRACTING"
  | "INGESTING"
  | "PENDING_REVIEW"
  | "READY"
  | "FAILED"
  | "PENDING_DELETE";

export interface BrandCreateRequest {
  name: string;
  website_url?: string;
  dna_source: DnaSource;
  manual_hints?: Record<string, unknown>;
  uploaded_source_ids?: string[];
}

export interface BrandCreateResponse {
  brand_id: string;
  status: BrandStatus;
  dna_source: DnaSource;
  job_id: string | null;
}

export interface ActiveJobSummary {
  id: string;
  status: string;
  stage: string | null;
  progress: Record<string, unknown>;
}

// channel_readiness is keyed by provider: wordpress | shopify | webflow | custom_api
export interface BrandSummary {
  id: string;
  name: string;
  website_url: string | null;
  dna_source: DnaSource;
  status: BrandStatus;
  failure_reason: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  channel_readiness: Record<string, string | null>;
  active_job: ActiveJobSummary | null;
}

export interface BrandListResponse {
  items: BrandSummary[];
}

export interface ApproveBrandResponse {
  brand_id: string;
  status: BrandStatus;
  locked_at: string;
  locked_by: string;
}

// DELETE /v1/brands/{id} returns { deleted: true, brand_id }
export interface DeleteBrandResponse {
  deleted: boolean;
  brand_id: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Brand profile (DNA) — backend/app/schemas/brand_profile.py
// ─────────────────────────────────────────────────────────────────────────────
export type PublishAdapter = "none" | "wordpress" | "shopify" | "webflow" | "custom_api";

export interface InternalLink {
  label: string;
  url: string;
}

// POST body for manual DNA submission (BrandProfileContent)
export interface BrandProfileContent {
  name: string;
  site_url?: string | null;
  one_liner: string;
  industry?: string | null;
  allowed_topics: string[];
  disallowed_topics?: string[];
  audience_personas: string[];
  tone_rules: string;
  banned_phrases?: string[];
  unique_angle: string;
  ctas: string[];
  proof_points?: string[];
  messaging_guardrails?: string[];
  compliance_keywords?: string[];
  image_subject_hints?: string | null;
  image_palette?: string | null;
  visual_direction?: string | null;
}

// Full profile (BrandProfileContent + OperationalConfig + metadata)
export interface BrandProfileFull extends BrandProfileContent {
  id: string;
  brand_id: string;
  internal_links: InternalLink[];
  placid_template_id: string | null;
  image_output_bucket: string | null;
  default_location: string;
  default_language: string;
  publish_adapter: PublishAdapter;
  publish_config: Record<string, unknown>;
  generation_source: string;
  prompt_version: string | null;
  extraction_model: string | null;
  locked: boolean;
  locked_at: string | null;
  locked_by: string | null;
  created_at: string;
  updated_at: string;
}

// PATCH accepts any subset of content + operational fields.
export type BrandProfilePatch = Partial<
  BrandProfileContent & {
    internal_links: InternalLink[];
    placid_template_id: string | null;
    image_output_bucket: string | null;
    default_location: string;
    default_language: string;
    publish_adapter: PublishAdapter;
    publish_config: Record<string, unknown>;
  }
>;

// ─────────────────────────────────────────────────────────────────────────────
// Jobs — backend/app/schemas/job.py
// ─────────────────────────────────────────────────────────────────────────────
export interface JobRead {
  id: string;
  org_id: string | null;
  brand_id: string | null;
  job_type: string; // keyword_research | serp_analysis | content_generation | brand.onboard | reingest
  status: string; // NEW | QUEUED | RUNNING | PROCESSING | SUCCEEDED | FAILED
  stage: string | null;
  progress: Record<string, unknown>;
  attempt_count: number;
  max_attempts: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Pipeline 1 — Keyword research — backend/app/schemas/keyword.py
// ─────────────────────────────────────────────────────────────────────────────
export interface KeywordResearchRequest {
  seed_keyword: string;
}

export interface KeywordResearchResponse {
  job_id: string;
  brand_id: string;
  seed_keyword: string;
  status: string;
  message: string;
}

export interface KeywordOut {
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
}

export type KeywordResearchStatus = "never_run" | "processing" | "completed" | "failed";

export interface KeywordListResponse {
  keywords: KeywordOut[];
  total: number;
  brand_id: string;
  latest_job_id: string | null;
  research_status: KeywordResearchStatus;
}

export interface KeywordStatsResponse {
  total_keywords: number;
  avg_search_volume: number | null;
  avg_difficulty: number | null;
  top_sources: Record<string, number>;
  completion_rate: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Pipeline 2 — SERP analysis — backend returns plain dicts (routers/brands.py)
// ─────────────────────────────────────────────────────────────────────────────
export interface SerpCompetitor {
  url: string;
  title: string | null;
  content_strength: number | null;
  content_gaps: string[];
  competitive_advantage: string | null;
}

export interface SerpAnalysisItem {
  id: string;
  keyword_text: string;
  status: string; // PENDING | PROCESSING | COMPLETED | FAILED
  total_results_analyzed: number;
  avg_word_count: number | null;
  content_gap_score: number | null;
  created_at: string;
  competitors: SerpCompetitor[];
}

export interface SerpAnalysisResponse {
  serp_analyses: SerpAnalysisItem[];
  total_analyses: number;
  latest_job_id: string | null;
  analysis_status: string; // job.status lowercased, or "never_run"
}

// POST /v1/brands/{id}/serp-analysis response
export interface SerpAnalysisStartResponse {
  job_id: string;
  brand_id: string;
  keywords_count: number;
  status: string;
  message: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Pipeline 3 — Content generation — backend/app/schemas/content_generation.py
// ─────────────────────────────────────────────────────────────────────────────
export interface ContentGenerationRequest {
  keyword: string;
  serp_analysis_job_id?: string | null;
}

export interface ContentGenerationResponse {
  job_id: string;
  status: string;
  message: string;
}

// GET /v1/brands/{id}/pipeline-status
export interface PipelineJobInfo {
  id: string;
  status: string;
  stage: string | null;
  created_at: string;
  auto_triggered: boolean;
  auto_triggered_from: string | null;
}

export interface PipelineStatusResponse {
  brand_id: string;
  brand_name: string;
  keyword_count: number;
  pipeline_status: {
    pipeline_1_keyword_research: PipelineJobInfo[];
    pipeline_2_serp_analysis: PipelineJobInfo[];
    pipeline_3_content_generation: PipelineJobInfo[];
  };
  auto_trigger_stats: { successful: number; failed: number; skipped: number };
  auto_trigger_enabled: boolean;
  last_updated: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Blogs (content review) — backend/app/schemas/blog.py
// ─────────────────────────────────────────────────────────────────────────────
export type BlogJobStatus =
  | "NEW"
  | "GENERATING"
  | "WRITING"
  | "RESEARCHING"
  | "BRIEFING"
  | "PENDING_BRIEF_REVIEW"
  | "PENDING_REVIEW"
  | "PUBLISHING"
  | "PUBLISHED"
  | "FAILED"
  | "REJECTED";

export interface BlogJobCreate {
  keyword: string;
}

export interface BlogBriefOut {
  id: string;
  job_id: string;
  selected_title: string;
  title_options: string[];
  meta_description: string;
  search_intent: string;
  target_word_count: number;
  target_audience: string | null;
  keyword_variants: string[];
  outline: Record<string, unknown>[];
  aeo: Record<string, unknown>;
  tags: string[];
  approved: boolean;
  created_at: string;
}

export interface BlogDraftOut {
  id: string;
  job_id: string;
  title: string;
  meta_description: string;
  html_content: string;
  word_count: number;
  seo_score: number;
  aeo_score: number;
  virality_score: number;
  featured_image_url: string | null;
  approved: boolean;
  created_at: string;
}

export interface BlogJobOut {
  id: string;
  brand_id: string;
  keyword: string;
  status: BlogJobStatus | string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  brief: BlogBriefOut | null;
  draft: BlogDraftOut | null;
}

export interface BlogJobListResponse {
  items: BlogJobOut[];
}

export interface ApproveBriefRequest {
  selected_title?: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Brand knowledge sources — backend/app/routers/brand_sources.py
// ─────────────────────────────────────────────────────────────────────────────
export type SourceType = "manual_text" | "uploaded_doc";

export interface AddSourceRequest {
  source_type: SourceType;
  title?: string | null;
  storage_key?: string | null;
  raw_text?: string | null;
  metadata?: Record<string, unknown>;
}

export interface BrandSource {
  id: string;
  brand_id: string;
  source_type: string;
  title: string | null;
  url: string | null;
  storage_key: string | null;
  word_count: number | null;
  fetched_at: string | null;
  created_at: string | null;
  metadata: Record<string, unknown>;
}

export interface BrandSourceListResponse {
  items: BrandSource[];
  total: number;
}

export interface AddSourceResponse {
  source_id: string;
  ingest_job_id: string | null;
}

export interface ReingestResponse {
  job_id: string;
  sources_count: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Integrations — backend/app/routers/integrations.py
// ─────────────────────────────────────────────────────────────────────────────
export type IntegrationProvider = "wordpress" | "webhook" | "shopify" | "webflow";

// legacy ("format=legacy", default) shape from _account_to_dict
export interface IntegrationAccount {
  id: string;
  brand_id: string;
  provider: string;
  status: string; // active | pending | failed | testing
  display_label: string | null;
  config: Record<string, unknown>;
  last_tested_at: string | null;
  last_error: string | null;
  created_at: string | null;
}

export interface IntegrationListResponse {
  items: IntegrationAccount[];
}

// channel ("format=channel") shape from _account_to_channel_integration
export interface ChannelIntegration {
  id: string;
  brand_id: string;
  channel_type: string; // wordpress | webhook | shopify | ghost
  name: string;
  status: string; // connected | disconnected | error | testing
  config: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface WordPressSetupRequest {
  site_url: string;
  username: string;
  application_password: string;
  default_status?: string;
  default_categories?: number[];
  default_author_id?: number | null;
}

export interface WordPressTestRequest {
  site_url: string;
  username: string;
  password: string;
  auth_type?: string;
  custom_post_type?: string;
  auto_publish?: boolean;
}

export interface IntegrationTestResponse {
  ok?: boolean;
  success: boolean;
  error?: string | null;
  site_info?: Record<string, unknown>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Scheduling & publishing — routers/schedules.py + routers/publishing.py
// ─────────────────────────────────────────────────────────────────────────────
export interface BulkScheduleItem {
  date: string; // YYYY-MM-DD
  keyword: string;
}

export interface BulkScheduleRequest {
  items: BulkScheduleItem[];
  time: string; // HH:MM
  timezone_str: string;
  channels?: string[];
}

export interface BulkScheduleCreated {
  schedule_id: string;
  blog_job_id: string;
  keyword: string;
  scheduled_at: string;
}

export interface BulkScheduleResponse {
  created: BulkScheduleCreated[];
  count: number;
}

export interface ScheduleRead {
  id: string;
  title: string;
  scheduled_at: string;
  brand_id: string;
  blog_job_id: string | null;
  target_keyword: string | null;
  target_channels: string[];
  status: string;
  published_urls: Record<string, string>;
  last_error: string | null;
  created_at: string;
}

export interface CalendarEntry {
  id: string;
  title: string;
  scheduled_at: string;
  status: string;
  target_keyword: string | null;
  target_channels: string[];
  blog_job_id: string | null;
  published_urls: Record<string, string>;
  last_error: string | null;
}

export interface PublishingChannelStat {
  channel: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
}

export interface PublishingStatsResponse {
  brand_id: string;
  period_days: number;
  total_schedules: number;
  published_count: number;
  failed_count: number;
  pending_count: number;
  success_rate: number;
  channel_stats: PublishingChannelStat[];
  recent_activity: Array<{
    id: string;
    title: string;
    status: string;
    published_at: string | null;
    channels: string[];
    published_urls: Record<string, string>;
  }>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Superadmin — backend/app/schemas/superadmin.py
// ─────────────────────────────────────────────────────────────────────────────
export interface OrgListItem {
  id: string;
  name: string;
  plan_code: string;
  status: string;
  user_count: number;
  brand_count: number;
}

export interface OrgListResponse {
  items: OrgListItem[];
}

export interface CreateOrgRequest {
  organization_name: string;
  plan_code: string;
  admin_name: string;
  admin_email: string;
}

export interface CreateOrgResponse {
  org_id: string;
  admin_user_id: string;
}

export interface UpdateOrgRequest {
  name?: string;
  plan_code?: string;
}

export interface OrgUserOut {
  id: string;
  name: string | null;
  email: string;
  role: string;
  email_verified: boolean;
  disabled: boolean;
}

export interface OrgUserListResponse {
  items: OrgUserOut[];
}

export interface CreateOrgUserRequest {
  name: string;
  email: string;
  role: string;
}

export interface UpdateOrgUserRequest {
  role?: string;
  disabled?: boolean;
}
