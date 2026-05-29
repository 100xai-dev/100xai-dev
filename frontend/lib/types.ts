// These types are hand-mirrored from the backend Pydantic schemas. To regenerate
// authoritative types from the live FastAPI OpenAPI doc, run:
//
//   BACKEND_URL=http://localhost:8000 pnpm gen:api-types
//
// That writes `lib/api-types.ts`; you can then import `components["schemas"]["BrandSummary"]`
// instead of the hand types below. Until the migration is complete, the hand types
// remain the source of truth so the frontend builds without a running backend.

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

export interface ActiveJobSummary {
  id: string;
  status: string;
  stage: string | null;
  progress: Record<string, unknown>;
}

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

export interface BrandCreateResponse {
  brand_id: string;
  status: BrandStatus;
  dna_source: DnaSource;
  job_id: string | null;
}

export interface DeleteBrandResponse {
  job_id: string;
}

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

export interface InternalLink {
  label: string;
  url: string;
}

export type PublishAdapter = "none" | "wordpress" | "shopify" | "webflow" | "custom_api";

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

export interface ApproveBrandResponse {
  brand_id: string;
  status: BrandStatus;
  locked_at: string;
  locked_by: string;
}

export interface JobRead {
  id: string;
  org_id: string | null;
  brand_id: string | null;
  job_type: string;
  status: string;
  stage: string | null;
  progress: Record<string, unknown>;
  attempt_count: number;
  max_attempts: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

