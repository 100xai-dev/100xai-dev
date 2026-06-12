// Backend base URL is needed on both server and client (client only as fallback —
// the client normally calls the same-origin Next proxy at /api/*).
const backendBaseUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.BACKEND_URL ?? "http://localhost:8000";

// The admin API token is server-only. Never read NEXT_PUBLIC_API_TOKEN here —
// that would bundle the token into client JS. Mutations from the browser go
// through the Next route-handler proxy, which injects the token server-side.
const apiToken = process.env.API_TOKEN ?? "";

export function getBackendBaseUrl(): string {
  return backendBaseUrl.replace(/\/$/, "");
}

export function getServerApiToken(): string {
  return apiToken;
}

export function isDemoMode(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true";
}
