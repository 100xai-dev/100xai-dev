"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import type { UserOut, OrgOut, AuthResponse } from "@/lib/types";
import {
  clearSession,
  getStoredOrg,
  getStoredUser,
  getValidAccessToken,
  getRefreshToken,
  saveSession,
} from "@/lib/auth";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

type AuthState = {
  user: UserOut | null;
  org: OrgOut | null;
  accessToken: string | null;
  loading: boolean;
};

type AuthContextValue = AuthState & {
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string, orgName: string) => Promise<void>;
  verifyEmail: (token: string) => Promise<void>;
  resendVerification: (email: string) => Promise<void>;
  logout: () => Promise<void>;
  getToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    user: null,
    org: null,
    accessToken: null,
    loading: true,
  });

  useEffect(() => {
    const user = getStoredUser();
    const org = getStoredOrg();
    if (user && org) {
      getValidAccessToken().then((token) => {
        setState({ user, org, accessToken: token, loading: false });
      });
    } else {
      setState((s) => ({ ...s, loading: false }));
    }
  }, []);

  const applySession = useCallback((data: AuthResponse) => {
    saveSession(data);
    setState({
      user: data.user,
      org: data.organization,
      accessToken: data.access_token,
      loading: false,
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${BACKEND}/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as {
        detail?: string | { code?: string; email?: string };
      };
      // Unverified accounts are blocked at login — route to the verify-email notice.
      if (res.status === 403 && typeof err.detail === "object" && err.detail?.code === "email_not_verified") {
        router.push(`/verify-email?email=${encodeURIComponent(err.detail.email ?? email)}`);
        return;
      }
      throw new Error(typeof err.detail === "string" ? err.detail : "Login failed");
    }
    applySession(await res.json() as AuthResponse);
    router.push("/brands");
    // Invalidate the Next.js Router Cache so server components (e.g. /brands)
    // re-render with the new session instead of replaying the prior user's RSC.
    router.refresh();
  }, [applySession, router]);

  const signup = useCallback(async (
    name: string,
    email: string,
    password: string,
    orgName: string,
  ) => {
    const res = await fetch(`${BACKEND}/v1/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, organization_name: orgName, accept_terms: true }),
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new Error(typeof err.detail === "string" ? err.detail : "Signup failed");
    }
    // No session is issued until the email is verified.
    router.push(`/verify-email?email=${encodeURIComponent(email)}`);
  }, [router]);

  const verifyEmail = useCallback(async (token: string) => {
    const res = await fetch(`${BACKEND}/v1/auth/verify-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new Error(typeof err.detail === "string" ? err.detail : "Verification failed");
    }
    applySession(await res.json() as AuthResponse);
    router.push("/brands");
    router.refresh();
  }, [applySession, router]);

  const resendVerification = useCallback(async (email: string) => {
    await fetch(`${BACKEND}/v1/auth/resend-verification`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    }).catch(() => {});
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await fetch(`${BACKEND}/v1/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {});
    }
    clearSession();
    setState({ user: null, org: null, accessToken: null, loading: false });
    router.push("/login");
    // Clear cached server-rendered routes so the next user can't see stale brands.
    router.refresh();
  }, [router]);

  const getToken = useCallback(async () => {
    const token = await getValidAccessToken();
    if (token !== state.accessToken) {
      setState((s) => ({ ...s, accessToken: token }));
      // Ensure cookie is synced when token changes
      if (token) {
        document.cookie = `100xai_access_token=${token}; path=/; max-age=900; SameSite=Lax`;
      }
    }
    return token;
  }, [state.accessToken]);

  return (
    <AuthContext.Provider value={{ ...state, login, signup, verifyEmail, resendVerification, logout, getToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
