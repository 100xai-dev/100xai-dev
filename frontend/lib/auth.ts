import type { AuthResponse, UserOut, OrgOut } from "@/lib/types";

const ACCESS_TOKEN_KEY = "100xai_access_token";
const REFRESH_TOKEN_KEY = "100xai_refresh_token";
const USER_KEY = "100xai_user";
const ORG_KEY = "100xai_org";

export function saveSession(data: AuthResponse): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  localStorage.setItem(ORG_KEY, JSON.stringify(data.organization));
  // Sync to cookie so Next.js middleware can read it for route protection
  document.cookie = `${ACCESS_TOKEN_KEY}=${data.access_token}; path=/; max-age=900; SameSite=Lax`;
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(ORG_KEY);
  document.cookie = `${ACCESS_TOKEN_KEY}=; path=/; max-age=0`;
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): UserOut | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as UserOut) : null;
}

export function getStoredOrg(): OrgOut | null {
  const raw = localStorage.getItem(ORG_KEY);
  return raw ? (JSON.parse(raw) as OrgOut) : null;
}

export function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp * 1000 < Date.now() + 30_000; // 30s buffer
  } catch {
    return true;
  }
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  try {
    const res = await fetch(`${BACKEND}/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      clearSession();
      return null;
    }
    const data = (await res.json()) as { access_token: string };
    localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
    return data.access_token;
  } catch {
    return null;
  }
}

export async function getValidAccessToken(): Promise<string | null> {
  const token = getAccessToken();
  if (!token) return null;
  if (isTokenExpired(token)) {
    return refreshAccessToken();
  }
  return token;
}
