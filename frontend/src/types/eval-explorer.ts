// ---------------------------------------------------------------------------
// Assessment & Trace types
// ---------------------------------------------------------------------------

export interface AssessmentDetail {
  name: string;
  raw_value: string | number | boolean;
  normalized_score: number | null;
  passed: boolean | null;
  rationale: string | null;
  source_type: string;
}

export interface TraceDetail {
  trace_id: string;
  case_id: string;
  user_prompt: string;
  assistant_response: string;
  duration_ms: number | null;
  error: string | null;
  session_id: string | null;
  assessments: AssessmentDetail[];
}

export interface SessionGroup {
  session_id: string;
  eval_type: string;
  traces: TraceDetail[];
  session_assessment: AssessmentDetail | null;
}

export interface TracesResponse {
  traces: TraceDetail[];
  sessions: SessionGroup[];
}

// ---------------------------------------------------------------------------
// Run types
// ---------------------------------------------------------------------------

export interface RunSummary {
  run_id: string;
  timestamp: string;
  params: Record<string, string>;
  metrics: Record<string, number>;
  universal_quality: number | null;
  trace_count: number;
}

export interface RunsResponse {
  runs: RunSummary[];
}

// ---------------------------------------------------------------------------
// Experiment types
// ---------------------------------------------------------------------------

export interface ExperimentSummary {
  experiment_id: string;
  name: string;
  eval_type: string;
  run_count: number;
  last_run_timestamp: string | null;
  latest_pass_rate: number | null;
  latest_universal_quality: number | null;
}

export interface ExperimentsResponse {
  experiments: ExperimentSummary[];
}

// ---------------------------------------------------------------------------
// Quality trend types
// ---------------------------------------------------------------------------

export interface QualityTrendPoint {
  eval_type: string;
  timestamp: string;
  universal_quality: number;
  run_id: string;
}

export interface QualityTrendResponse {
  points: QualityTrendPoint[];
}

// ---------------------------------------------------------------------------
// Dataset types
// ---------------------------------------------------------------------------

export interface DatasetCase {
  id: string;
  user_prompt: string;
  rubric: string | null;
  tags: string[];
  extra: Record<string, unknown>;
}

export interface DatasetDetail {
  name: string;
  file_path: string;
  version: string;
  description: string;
  case_count: number;
  cases: DatasetCase[];
}

export interface DatasetsResponse {
  datasets: DatasetDetail[];
}

// ---------------------------------------------------------------------------
// Agent version types
// ---------------------------------------------------------------------------

export interface ExperimentResult {
  experiment_name: string;
  experiment_id: string;
  eval_type: string;
  run_count: number;
  pass_rate: number | null;
  average_quality: number | null;
  latest_run_id: string | null;
}

export interface AgentVersionSummary {
  model_id: string;
  name: string;
  git_branch: string;
  git_commit: string;
  git_commit_short: string;
  git_dirty: boolean;
  creation_timestamp: string;
  aggregate_quality: number | null;
  experiment_count: number;
  total_traces: number;
}

export interface AgentVersionDetail extends AgentVersionSummary {
  git_diff: string;
  git_repo_url: string;
  experiment_results: ExperimentResult[];
}

export interface AgentVersionsResponse {
  agents: AgentVersionSummary[];
}
