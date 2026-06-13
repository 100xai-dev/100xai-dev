// Backend base URL is needed on both server and client (client only as fallback —
// the client normally calls the same-origin Next proxy at /api/*).
const backendBaseUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.BACKEND_URL ?? "http://localhost:8000";

export function getBackendBaseUrl(): string {
  return backendBaseUrl.replace(/\/$/, "");
}

export function isDemoMode(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true";
}
