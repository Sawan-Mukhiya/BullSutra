import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import type { UserSession } from "@/types";

export function useSession() {
  return useQuery<UserSession>({
    queryKey: qk.session(),
    queryFn: async () => {
      const res = await fetch("/api/auth/session");
      if (!res.ok) return { authenticated: false };
      return res.json();
    },
    staleTime: 60 * 1000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || "Invalid credentials");
      }
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.session() });
    },
  });
}

export function useSignup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail?.[0]?.msg || "Failed to create account");
      }
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.session() });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await fetch("/api/auth/logout", { method: "POST" });
    },
    onSuccess: () => {
      qc.setQueryData(qk.session(), { authenticated: false });
    },
  });
}
