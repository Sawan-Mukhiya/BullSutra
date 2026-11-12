import { NextRequest, NextResponse } from "next/server";
import { readAuthCookies, setAuthCookies, clearAuthCookies } from "@/lib/auth-cookies";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 300;

const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://localhost:8000";

async function handleProxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const pathStr = path.join("/");

  // Path verification: allow only api/v1/*
  if (!pathStr.startsWith("api/v1/")) {
    return NextResponse.json(
      { error: { code: "not_found", message: "Invalid proxy endpoint" } },
      { status: 404 }
    );
  }

  // Block dedicated auth routes
  if (pathStr === "api/v1/auth/login" || pathStr === "api/v1/auth/refresh") {
    return NextResponse.json(
      { error: { code: "not_found", message: "Use dedicated auth endpoints" } },
      { status: 404 }
    );
  }

  const { search } = new URL(req.url);
  const upstreamUrl = `${API_INTERNAL_URL}/${pathStr}${search}`;

  let { access, refresh } = readAuthCookies(req);
  let newTokens: { access_token: string; refresh_token?: string } | null = null;

  // Refresh if access token missing but refresh token present
  if (!access && refresh) {
    try {
      const refreshRes = await fetch(`${API_INTERNAL_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (refreshRes.ok) {
        newTokens = await refreshRes.json();
        access = newTokens?.access_token;
      }
    } catch {
      // Ignore refresh error
    }
  }

  // Forward request headers
  const forwardHeaders = new Headers();
  const allowedHeaders = ["content-type", "accept", "last-event-id", "x-request-id"];
  for (const [key, value] of req.headers.entries()) {
    if (allowedHeaders.includes(key.toLowerCase())) {
      forwardHeaders.set(key, value);
    }
  }

  if (access) {
    forwardHeaders.set("Authorization", `Bearer ${access}`);
  }

  let body: BodyInit | undefined = undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = req.body as any;
  }

  const fetchOptions: any = {
    method: req.method,
    headers: forwardHeaders,
    body,
    cache: "no-store",
  };

  // Node fetch duplex requirement for request streaming / multipart
  if (body) {
    fetchOptions.duplex = "half";
  }

  try {
    let upstreamRes = await fetch(upstreamUrl, fetchOptions);

    // If 401 on non-streaming and refresh token exists, retry once
    const isSSE = forwardHeaders.get("accept")?.includes("text/event-stream");
    if (upstreamRes.status === 401 && refresh && !newTokens && !isSSE) {
      const retryRefresh = await fetch(`${API_INTERNAL_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (retryRefresh.ok) {
        newTokens = await retryRefresh.json();
        if (newTokens?.access_token) {
          forwardHeaders.set("Authorization", `Bearer ${newTokens.access_token}`);
          upstreamRes = await fetch(upstreamUrl, fetchOptions);
        }
      }
    }

    const responseHeaders = new Headers();
    const headersToCopy = ["content-type", "content-disposition", "x-request-id", "cache-control"];
    for (const [k, v] of upstreamRes.headers.entries()) {
      if (headersToCopy.includes(k.toLowerCase())) {
        responseHeaders.set(k, v);
      }
    }

    const contentType = upstreamRes.headers.get("content-type") || "";
    if (contentType.includes("text/event-stream")) {
      responseHeaders.set("Cache-Control", "no-cache, no-transform");
      responseHeaders.set("Connection", "keep-alive");
      responseHeaders.set("X-Accel-Buffering", "no");
    }

    const response = new NextResponse(upstreamRes.body, {
      status: upstreamRes.status,
      statusText: upstreamRes.statusText,
      headers: responseHeaders,
    });

    if (newTokens) {
      setAuthCookies(response, newTokens);
    }

    return response;
  } catch (err: any) {
    return NextResponse.json(
      {
        error: {
          code: "upstream_unavailable",
          message: err?.message || "FastAPI upstream service is unreachable",
          details: { upstreamUrl },
        },
      },
      { status: 503 }
    );
  }
}

export { handleProxy as GET, handleProxy as POST, handleProxy as DELETE };
