import { useState, useEffect, useRef } from "react";
import type { JobEvent } from "@/types";

export type NodeStatus = "pending" | "running" | "done" | "failed" | "skipped";

export interface JobEventsState {
  events: JobEvent[];
  status: "idle" | "connecting" | "running" | "succeeded" | "failed";
  progress: number;
  phase: string | null;
  nodes: Record<string, NodeStatus>;
  nodeResults: Record<string, any>;
  result: any | null;
  error: string | null;
}

export function useJobEvents(jobId: string | null): JobEventsState {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [status, setStatus] = useState<JobEventsState["status"]>("idle");
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<string | null>(null);
  const [nodes, setNodes] = useState<Record<string, NodeStatus>>({});
  const [nodeResults, setNodeResults] = useState<Record<string, any>>({});
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const seenSeqs = useRef<Set<number>>(new Set());
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) {
      setStatus("idle");
      return;
    }

    seenSeqs.current.clear();
    setEvents([]);
    setProgress(0);
    setPhase(null);
    setNodes({});
    setNodeResults({});
    setResult(null);
    setError(null);
    setStatus("connecting");

    const url = `/api/proxy/api/v1/agents/runs/${jobId}/events`;
    const es = new EventSource(url);
    esRef.current = es;

    const handleEvent = (eventName: string, e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data);
        const seq = parsed.seq ?? Date.now();
        if (seenSeqs.current.has(seq)) return;
        seenSeqs.current.add(seq);

        const jobEvent: JobEvent = {
          event: eventName,
          seq,
          data: parsed.data ?? parsed,
        };

        setEvents((prev) => [...prev, jobEvent]);

        switch (eventName) {
          case "job_started":
            setStatus("running");
            break;
          case "node_started":
            if (jobEvent.data.node) {
              setNodes((prev) => ({ ...prev, [jobEvent.data.node!]: "running" }));
            }
            break;
          case "node_finished":
            if (jobEvent.data.node) {
              setNodes((prev) => ({ ...prev, [jobEvent.data.node!]: "done" }));
              setNodeResults((prev) => ({ ...prev, [jobEvent.data.node!]: jobEvent.data }));
            }
            break;
          case "progress":
            if (typeof jobEvent.data.value === "number") {
              setProgress(jobEvent.data.value);
            }
            if (jobEvent.data.phase) {
              setPhase(String(jobEvent.data.phase));
            }
            break;
          case "job_finished":
            setStatus("succeeded");
            setResult(jobEvent.data);
            setProgress(100);
            es.close();
            break;
          case "job_failed":
            setStatus("failed");
            setError(jobEvent.data.error || "Job execution failed");
            es.close();
            break;
          case "end":
            es.close();
            break;
        }
      } catch (err) {
        console.error("Failed to parse SSE event", err);
      }
    };

    const eventNames = [
      "job_started",
      "node_started",
      "node_finished",
      "progress",
      "log",
      "job_finished",
      "job_failed",
      "end",
    ];

    for (const name of eventNames) {
      es.addEventListener(name, (e: MessageEvent) => handleEvent(name, e));
    }

    es.onerror = () => {
      if (status !== "succeeded" && status !== "failed") {
        // Keep connecting unless closed
      }
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [jobId]);

  return {
    events,
    status,
    progress,
    phase,
    nodes,
    nodeResults,
    result,
    error,
  };
}
