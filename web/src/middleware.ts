import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/auth-cookies";

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;

  if (pathname.startsWith("/admin")) {
    const hasAccess = req.cookies.has(ACCESS_COOKIE);
    const hasRefresh = req.cookies.has(REFRESH_COOKIE);

    if (!hasAccess && !hasRefresh) {
      const loginUrl = new URL("/login", req.url);
      const nextPath = `${pathname}${search}`;
      loginUrl.searchParams.set("next", nextPath);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"],
};
