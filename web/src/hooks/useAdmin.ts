import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type {
  AdminStatsResponse,
  WeightsOut,
  CalibrationOut,
  JobOut,
} from "@/types";

export function useAdminStats() {
  return useQuery({
    queryKey: qk.adminStats(),
    queryFn: async () => {
      const res = await api.GET("/api/v1/admin/stats");
      return unwrap<AdminStatsResponse>(res);
    },
    staleTime: 15 * 1000,
    refetchInterval: 15 * 1000,
  });
}

export function useFreshness() {
  return useQuery({
    queryKey: qk.freshness(),
    queryFn: async () => {
      const res = await api.GET("/api/v1/health/data-freshness");
      return unwrap<Record<string, any>>(res);
    },
    staleTime: 60 * 1000,
  });
}

export function useWeights() {
  return useQuery({
    queryKey: qk.weights(),
    queryFn: async () => {
      const res = await api.GET("/api/v1/agents/weights/latest");
      return unwrap<WeightsOut>(res);
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useCalibration() {
  return useQuery({
    queryKey: qk.calibration(),
    queryFn: async () => {
      const res = await api.GET("/api/v1/agents/calibration");
      return unwrap<CalibrationOut>(res);
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useJobs(kind?: string, status?: string, offset = 0, limit = 20) {
  return useQuery({
    queryKey: qk.jobs(kind, status, offset, limit),
    queryFn: async () => {
      const res = await api.GET("/api/v1/jobs", {
        params: {
          query: {
            kind,
            status,
            offset,
            limit,
          },
        },
      });
      return unwrap<{ items: JobOut[]; total: number }>(res);
    },
    staleTime: 5 * 1000,
    refetchInterval: 10 * 1000,
  });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: qk.job(id),
    queryFn: async () => {
      const res = await api.GET("/api/v1/jobs/{job_id}", {
        params: {
          path: { job_id: id },
        },
      });
      return unwrap<JobOut>(res);
    },
    enabled: Boolean(id),
    staleTime: 3 * 1000,
  });
}

export function useRunAgents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { symbol: string; as_of?: string; use_llm?: boolean; force?: boolean }) => {
      const res = await api.POST("/api/v1/agents/run", {
        body: {
          symbol: payload.symbol,
          as_of: payload.as_of ?? null,
          use_llm: payload.use_llm ?? true,
          force: payload.force ?? false,
        },
      });
      return unwrap<{ job_id?: string | null; status: "queued" | "cached"; brief_id?: string | null }>(res as any);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["latestBriefs"] });
    },
  });
}

export function useRunPipeline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, payload }: { name: string; payload?: Record<string, unknown> }) => {
      const res = await api.POST("/api/v1/admin/pipelines/{name}/run", {
        params: { path: { name } },
        body: (payload ?? {}) as any,
      });
      return unwrap<{ job_id: string; status: string }>(res as any);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["freshness"] });
    },
  });
}
