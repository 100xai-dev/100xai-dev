export type DnaSource = "crawl" | "manual";
export type BrandStatus =
  | "DRAFT"
  | "CRAWLING"
  | "EXTRACTING"
  | "INGESTING"
  | "PENDING_REVIEW"
  | "READY"
  | "FAILED";

export interface BrandCreateRequest {
  name: string;
  website_url?: string;
  dna_source: DnaSource;
  manual_hints?: Record<string, unknown>;
  uploaded_source_ids?: string[];
}

