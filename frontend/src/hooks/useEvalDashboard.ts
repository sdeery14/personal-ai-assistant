"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api-client";
import type {
  TrendsResponse,
  TrendSummary,
  RegressionsResponse,
  RegressionReport,
  PromptsResponse,
  PromptListItem,
  PromotionGateResult,
  AuditRecord,
  EvalRunStatus,
  RollbackInfo,
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
// usePrompts
// ---------------------------------------------------------------------------

export function usePrompts() {
  const { data: session } = useSession();
  const [prompts, setPrompts] = useState<PromptListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<PromptsResponse>(
        "/admin/evals/prompts"
      );
      setPrompts(data.prompts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prompts");
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { prompts, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// usePromote
// ---------------------------------------------------------------------------

export function usePromote() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkGate = useCallback(
    async (
      promptName: string,
      fromAlias = "experiment",
      toAlias = "production",
      version?: number
    ): Promise<PromotionGateResult | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.post<PromotionGateResult>(
          "/admin/evals/promote/check",
          {
            prompt_name: promptName,
            from_alias: fromAlias,
            to_alias: toAlias,
            version: version ?? null,
          }
        );
        return result;
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to check promotion gate"
        );
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const executePromotion = useCallback(
    async (
      promptName: string,
      toAlias: string,
      version: number,
      force: boolean,
      reason: string
    ): Promise<AuditRecord | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.post<AuditRecord>(
          "/admin/evals/promote/execute",
          {
            prompt_name: promptName,
            to_alias: toAlias,
            version,
            force,
            reason,
          }
        );
        return result;
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to execute promotion"
        );
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return { checkGate, executePromotion, isLoading, error };
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
// useRollback
// ---------------------------------------------------------------------------

export function useRollback() {
  const [rollbackInfo, setRollbackInfo] = useState<RollbackInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getRollbackInfo = useCallback(
    async (promptName: string, alias = "production") => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.get<RollbackInfo>(
          "/admin/evals/rollback/info",
          { prompt_name: promptName, alias }
        );
        setRollbackInfo(result);
        return result;
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to get rollback info"
        );
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const executeRollback = useCallback(
    async (
      promptName: string,
      alias: string,
      previousVersion: number,
      reason: string
    ): Promise<AuditRecord | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.post<AuditRecord>(
          "/admin/evals/rollback/execute",
          {
            prompt_name: promptName,
            alias,
            previous_version: previousVersion,
            reason,
          }
        );
        return result;
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to execute rollback"
        );
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return { rollbackInfo, isLoading, error, getRollbackInfo, executeRollback };
}
