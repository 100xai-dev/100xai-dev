// Backend base URL is needed for server-side API calls and initial client setup.
// Client-side API calls should use the Next.js proxy at /api/* for proper JWT forwarding.
const backendBaseUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.BACKEND_URL ?? "http://localhost:8000";

export function getBackendBaseUrl(): string {
  return backendBaseUrl.replace(/\/$/, "");
}

export function isDemoMode(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true";
}
