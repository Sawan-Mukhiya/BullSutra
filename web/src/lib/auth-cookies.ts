import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export const ACCESS_COOKIE = "bs_access";
export const REFRESH_COOKIE = "bs_refresh";

const isSecure = process.env.COOKIE_SECURE === "true";

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
}

export function setAuthCookies(res: NextResponse, tokens: AuthTokens): NextResponse {
  if (tokens.access_token) {
    res.cookies.set(ACCESS_COOKIE, tokens.access_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: isSecure,
      path: "/",
      maxAge: tokens.expires_in ?? 3600, // default 1 hour
    });
  }

  if (tokens.refresh_token) {
    res.cookies.set(REFRESH_COOKIE, tokens.refresh_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: isSecure,
      path: "/",
      maxAge: 7 * 24 * 60 * 60, // 7 days
    });
  }

  return res;
}

export function clearAuthCookies(res: NextResponse): NextResponse {
  res.cookies.set(ACCESS_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: isSecure,
    path: "/",
    maxAge: 0,
  });

  res.cookies.set(REFRESH_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: isSecure,
    path: "/",
    maxAge: 0,
  });

  return res;
}

export function readAuthCookies(req: NextRequest) {
  const access = req.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  return { access, refresh };
}
