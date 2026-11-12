import { cookies } from "next/headers";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "./auth-cookies";

const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://localhost:8000";

export async function serverApi<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<{ data: T | null; status: number; ok: boolean }> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_COOKIE)?.value;
  const refreshToken = cookieStore.get(REFRESH_COOKIE)?.value;

  const url = `${API_INTERNAL_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = new Headers(options.headers);

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers,
      cache: "no-store",
    });
  } catch (err) {
    return { data: null, status: 503, ok: false };
  }

  // Token refresh logic if 401 and refresh token exists
  if (res.status === 401 && refreshToken) {
    try {
      const refreshRes = await fetch(`${API_INTERNAL_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        const newAccess = refreshData.access_token;
        if (newAccess) {
          headers.set("Authorization", `Bearer ${newAccess}`);
          res = await fetch(url, {
            ...options,
            headers,
            cache: "no-store",
          });
        }
      }
    } catch {
      // Refresh failed
    }
  }

  let data: T | null = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  return { data, status: res.status, ok: res.ok };
}
