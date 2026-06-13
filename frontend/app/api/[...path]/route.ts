import { NextRequest, NextResponse } from "next/server";

import { getBackendBaseUrl } from "@/lib/config";

export const dynamic = "force-dynamic";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
  "proxy-authenticate",
  "proxy-authorization",
  "host",
  "content-length",
]);

async function proxy(request: NextRequest, params: Promise<{ path: string[] }>): Promise<NextResponse> {
  const { path } = await params;
  const search = request.nextUrl.search;
  const upstreamUrl = `${getBackendBaseUrl()}/${path.join("/")}${search}`;

  const headers = new Headers();
  for (const [name, value] of request.headers.entries()) {
    if (!HOP_BY_HOP.has(name.toLowerCase())) {
      headers.set(name, value);
    }
  }
  // Forward the logged-in user's token. The browser sends the 100xai_access_token
  // cookie (set by lib/auth.ts on login/refresh); promote it to an Authorization
  // header when the client did not already attach one explicitly.
  if (!headers.has("authorization")) {
    const cookieToken = request.cookies.get("100xai_access_token")?.value;
    if (cookieToken) headers.set("authorization", `Bearer ${cookieToken}`);
  }

  const method = request.method.toUpperCase();
  const body = method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();

  const upstream = await fetch(upstreamUrl, {
    method,
    headers,
    body,
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export const GET = (req: NextRequest, ctx: Ctx) => proxy(req, ctx.params);
export const POST = (req: NextRequest, ctx: Ctx) => proxy(req, ctx.params);
export const PATCH = (req: NextRequest, ctx: Ctx) => proxy(req, ctx.params);
export const PUT = (req: NextRequest, ctx: Ctx) => proxy(req, ctx.params);
export const DELETE = (req: NextRequest, ctx: Ctx) => proxy(req, ctx.params);
