import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type { WorkerRuntime } from "../api/types";

const WORKER_RUNTIME_MIN_REFRESH_INTERVAL_MS = 15_000;

interface UseWorkerRuntimeOptions {
  refreshKey?: string;
  retainLastResultOnError?: boolean;
}

export function useWorkerRuntime({
  refreshKey = "",
  retainLastResultOnError = true,
}: UseWorkerRuntimeOptions = {}) {
  const [runtime, setRuntime] = useState<WorkerRuntime | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [reload, setReload] = useState(0);
  const [checking, setChecking] = useState(true);
  const requestInFlightRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const load = async () => {
      if (requestInFlightRef.current) return;
      requestInFlightRef.current = true;
      let refreshIntervalMs = WORKER_RUNTIME_MIN_REFRESH_INTERVAL_MS;
      try {
        const nextRuntime = await api.getWorkerRuntime();
        if (cancelled) return;
        setRuntime(nextRuntime);
        setError(null);
        refreshIntervalMs = Math.max(
          nextRuntime.pollIntervalSeconds * 1000,
          WORKER_RUNTIME_MIN_REFRESH_INTERVAL_MS,
        );
      } catch (caught) {
        if (cancelled) return;
        if (!retainLastResultOnError) setRuntime(null);
        setError(caught);
      }
      if (!cancelled) {
        requestInFlightRef.current = false;
        setChecking(false);
        timer = window.setTimeout(load, refreshIntervalMs);
      }
    };

    void load();
    return () => {
      cancelled = true;
      requestInFlightRef.current = false;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [refreshKey, reload, retainLastResultOnError]);

  function reloadStatus() {
    if (checking || requestInFlightRef.current) return;
    setChecking(true);
    setReload((value) => value + 1);
  }

  return { checking, error, reloadStatus, runtime };
}
