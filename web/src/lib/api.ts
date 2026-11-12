import createClient from "openapi-fetch";
import type { paths } from "@/types/api";

export const api = createClient<paths>({ baseUrl: "/api/proxy" });

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
    public requestId?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function unwrap<T>(res: { data?: T; error?: any; response: Response }): T {
  if (res.error || res.data === undefined) {
    const e = res.error?.error;
    throw new ApiError(
      res.response?.status ?? 500,
      e?.code ?? "unknown",
      e?.message ?? res.response?.statusText ?? "Request failed",
      e?.details,
      e?.request_id
    );
  }
  return res.data;
}
