import { getBackendBaseUrl, getServerApiToken } from "@/lib/config";
import type {
  ApproveBrandResponse,
  BrandCreateRequest,
  BrandCreateResponse,
  BrandListResponse,
  BrandProfileContent,
  BrandProfileFull,
  BrandSummary,
  DeleteBrandResponse,
  JobRead,
} from "@/lib/types";

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  cache?: RequestCache;
};

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
    const token = getServerApiToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
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
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (payload.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch {
      // no-op fallback to status text
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
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

export async function requestBrandDelete(brandId: string): Promise<DeleteBrandResponse> {
  return apiRequest<DeleteBrandResponse>(`/v1/brands/${brandId}`, { method: "DELETE" });
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
