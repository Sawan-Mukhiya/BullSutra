import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { readAuthCookies, setAuthCookies, clearAuthCookies } from "@/lib/auth-cookies";

const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const { access, refresh } = readAuthCookies(req);

  if (!access && !refresh) {
    return NextResponse.json({ authenticated: false });
  }

  let tokenToUse = access;
  let newTokens: { access_token: string; refresh_token?: string } | null = null;

  // Refresh if access token is missing
  if (!tokenToUse && refresh) {
    try {
      const refreshRes = await fetch(`${API_INTERNAL_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (refreshRes.ok) {
        newTokens = await refreshRes.json();
        tokenToUse = newTokens?.access_token;
      }
    } catch {
      // Refresh error
    }
  }

  if (!tokenToUse) {
    const res = NextResponse.json({ authenticated: false });
    return clearAuthCookies(res);
  }

  try {
    const meRes = await fetch(`${API_INTERNAL_URL}/api/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${tokenToUse}`,
      },
    });

    if (meRes.ok) {
      const userData = await meRes.json();
      const res = NextResponse.json({ authenticated: true, user: userData });
      if (newTokens) {
        setAuthCookies(res, newTokens);
      }
      return res;
    }

    // If 401 and refresh available, try refresh once
    if (meRes.status === 401 && refresh && !newTokens) {
      const retryRefresh = await fetch(`${API_INTERNAL_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (retryRefresh.ok) {
        const retryTokens = await retryRefresh.json();
        const retryMe = await fetch(`${API_INTERNAL_URL}/api/v1/auth/me`, {
          headers: {
            Authorization: `Bearer ${retryTokens.access_token}`,
          },
        });
        if (retryMe.ok) {
          const retryUserData = await retryMe.json();
          const res = NextResponse.json({ authenticated: true, user: retryUserData });
          return setAuthCookies(res, retryTokens);
        }
      }
    }

    const res = NextResponse.json({ authenticated: false });
    return clearAuthCookies(res);
  } catch {
    return NextResponse.json({ authenticated: false });
  }
}
