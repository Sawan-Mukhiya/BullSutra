import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { setAuthCookies } from "@/lib/auth-cookies";

const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${API_INTERNAL_URL}/api/v1/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    const response = NextResponse.json({ ok: true });
    return setAuthCookies(response, {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      expires_in: data.expires_in,
    });
  } catch (err: any) {
    return NextResponse.json(
      {
        error: {
          code: "upstream_unavailable",
          message: err?.message || "Could not connect to authentication service",
        },
      },
      { status: 503 }
    );
  }
}
