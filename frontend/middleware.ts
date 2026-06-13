import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/signup", "/verify-email", "/terms", "/privacy"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // The marketing landing page is always public — viewable logged in or out.
  // (Exact match: adding "/" to PUBLIC_PATHS would make every path public,
  // since every pathname startsWith "/".)
  if (pathname === "/") {
    return NextResponse.next();
  }

  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
  const token = request.cookies.get("100xai_access_token")?.value;

  if (!isPublic && !token) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isPublic && token) {
    const url = request.nextUrl.clone();
    url.pathname = "/brands";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
