"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api-client";
import type {
  TrendsResponse,
  TrendSummary,
  RegressionsResponse,
  RegressionReport,
  EvalRunStatus,
  RunDetail,
} from "@/types/eval-dashboard";

// ---------------------------------------------------------------------------
// useTrends
// ---------------------------------------------------------------------------

export function useTrends(evalType?: string, limit: number = 10) {
  const { data: session } = useSession();
  const [summaries, setSummaries] = useState<TrendSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = { limit };
      if (evalType) params.eval_type = evalType;
      const data = await apiClient.get<TrendsResponse>(
        "/admin/evals/trends",
        params
      );
      setSummaries(data.summaries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trends");
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken, evalType, limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { summaries, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useRegressions
// ---------------------------------------------------------------------------

export function useRegressions(evalType?: string) {
  const { data: session } = useSession();
  const [reports, setReports] = useState<RegressionReport[]>([]);
  const [hasRegressions, setHasRegressions] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {};
      if (evalType) params.eval_type = evalType;
      const data = await apiClient.get<RegressionsResponse>(
        "/admin/evals/regressions",
        params
      );
      setReports(data.reports);
      setHasRegressions(data.has_regressions);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load regressions"
      );
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken, evalType]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { reports, hasRegressions, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useEvalRun
// ---------------------------------------------------------------------------

export function useEvalRun() {
  const [status, setStatus] = useState<EvalRunStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startRun = useCallback(async (suite: string = "core") => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.post<EvalRunStatus>(
        "/admin/evals/run",
        { suite }
      );
      setStatus(result);
      return result;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start eval run"
      );
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.get<EvalRunStatus | null>(
        "/admin/evals/run/status"
      );
      setStatus(result);
      return result;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to get run status"
      );
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { status, isLoading, error, startRun, refreshStatus };
}

// ---------------------------------------------------------------------------
// useRunDetail
// ---------------------------------------------------------------------------

export function useRunDetail(runId?: string, evalType?: string) {
  const { data: session } = useSession();
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-fetch when runId and evalType are provided declaratively
  useEffect(() => {
    if (!session?.accessToken || !runId || !evalType) return;
    setIsLoading(true);
    setError(null);
    apiClient
      .get<RunDetail>(`/admin/evals/runs/${runId}/detail`, {
        eval_type: evalType,
      })
      .then(setDetail)
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : "Failed to load run detail"
        )
      )
      .finally(() => setIsLoading(false));
  }, [session?.accessToken, runId, evalType]);

  return { detail, isLoading, error };
}

