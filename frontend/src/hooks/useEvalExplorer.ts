"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api-client";
import type {
  ExperimentsResponse,
  ExperimentSummary,
  RunsResponse,
  RunSummary,
  TracesResponse,
  TraceDetail,
  SessionGroup,
  QualityTrendResponse,
  QualityTrendPoint,
  DatasetsResponse,
  DatasetDetail,
  AgentVersionsResponse,
  AgentVersionSummary,
  AgentVersionDetail,
} from "@/types/eval-explorer";

// ---------------------------------------------------------------------------
// useAgentVersions
// ---------------------------------------------------------------------------

export function useAgentVersions() {
  const { data: session } = useSession();
  const [agents, setAgents] = useState<AgentVersionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<AgentVersionsResponse>(
        "/admin/evals/explorer/agents"
      );
      setAgents(data.agents);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load agent versions"
      );
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { agents, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useAgentVersionDetail
// ---------------------------------------------------------------------------

export function useAgentVersionDetail(modelId: string | null) {
  const { data: session } = useSession();
  const [agent, setAgent] = useState<AgentVersionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken || !modelId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<AgentVersionDetail>(
        `/admin/evals/explorer/agents/${modelId}`
      );
      setAgent(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load agent version"
      );
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken, modelId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const clear = useCallback(() => {
    setAgent(null);
    setError(null);
  }, []);

  return { agent, isLoading, error, refresh, clear };
}

// ---------------------------------------------------------------------------
// useExperiments
// ---------------------------------------------------------------------------

export function useExperiments() {
  const { data: session } = useSession();
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<ExperimentsResponse>(
        "/admin/evals/explorer/experiments"
      );
      setExperiments(data.experiments);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load experiments"
      );
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { experiments, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useExperimentRuns
// ---------------------------------------------------------------------------

export function useExperimentRuns(
  experimentId: string | null,
  evalType: string | null
) {
  const { data: session } = useSession();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken || !experimentId || !evalType) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<RunsResponse>(
        `/admin/evals/explorer/experiments/${experimentId}/runs`,
        { eval_type: evalType }
      );
      setRuns(data.runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load runs");
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken, experimentId, evalType]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const clear = useCallback(() => {
    setRuns([]);
    setError(null);
  }, []);

  return { runs, isLoading, error, refresh, clear };
}

// ---------------------------------------------------------------------------
// useRunTraces
// ---------------------------------------------------------------------------

export function useRunTraces(runId: string | null, evalType: string | null) {
  const { data: session } = useSession();
  const [traces, setTraces] = useState<TraceDetail[]>([]);
  const [sessions, setSessions] = useState<SessionGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken || !runId || !evalType) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<TracesResponse>(
        `/admin/evals/explorer/runs/${runId}/traces`,
        { eval_type: evalType }
      );
      setTraces(data.traces);
      setSessions(data.sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load traces");
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken, runId, evalType]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const clear = useCallback(() => {
    setTraces([]);
    setSessions([]);
    setError(null);
  }, []);

  return { traces, sessions, isLoading, error, refresh, clear };
}

// ---------------------------------------------------------------------------
// useUniversalQualityTrend
// ---------------------------------------------------------------------------

export function useUniversalQualityTrend(limit: number = 20) {
  const { data: session } = useSession();
  const [points, setPoints] = useState<QualityTrendPoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<QualityTrendResponse>(
        "/admin/evals/explorer/trends/quality",
        { limit }
      );
      setPoints(data.points);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load quality trend"
      );
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken, limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { points, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useDatasets
// ---------------------------------------------------------------------------

export function useDatasets() {
  const { data: session } = useSession();
  const [datasets, setDatasets] = useState<DatasetDetail[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<DatasetsResponse>(
        "/admin/evals/explorer/datasets"
      );
      setDatasets(data.datasets);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load datasets"
      );
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { datasets, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useDatasetDetail
// ---------------------------------------------------------------------------

export function useDatasetDetail(datasetId: string | null) {
  const { data: session } = useSession();
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session?.accessToken || !datasetId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<DatasetDetail>(
        `/admin/evals/explorer/datasets/${datasetId}`
      );
      setDataset(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load dataset"
      );
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken, datasetId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const clear = useCallback(() => {
    setDataset(null);
    setError(null);
  }, []);

  return { dataset, isLoading, error, refresh, clear };
}
