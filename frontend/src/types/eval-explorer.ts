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
  dataset_id: string | null;
  git_sha: string | null;
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
  git_sha: string;
}

export interface QualityTrendResponse {
  points: QualityTrendPoint[];
}

// ---------------------------------------------------------------------------
// Dataset types
// ---------------------------------------------------------------------------

export interface DatasetCase {
  record_id: string;
  inputs: Record<string, unknown>;
  expectations: Record<string, unknown>;
  extra: Record<string, unknown>;
}

export interface DatasetDetail {
  dataset_id: string;
  name: string;
  dataset_type: string;
  version: string;
  source_file: string;
  case_count: number;
  experiment_ids: string[];
  created_time: string | null;
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

export interface GuardrailInfo {
  name: string;
  type: string;
}

export interface SpecialistInfo {
  name: string;
  type: string;
  model?: string;
  tools: string[];
  description: string;
}

export interface AgentGraphNode {
  id: string;
  label: string;
  type: string;
  tools?: string[];
}

export interface AgentGraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface AgentGraph {
  nodes: AgentGraphNode[];
  edges: AgentGraphEdge[];
}

export interface AgentConfig {
  model: string;
  name: string;
  framework: string;
  max_tokens: number | null;
  timeout_seconds: number | null;
  system_prompt: string;
  guardrails: GuardrailInfo[];
  specialists: SpecialistInfo[];
  graph: AgentGraph;
}

export interface AgentVersionSummary {
  model_id: string;
  name: string;
  git_branch: string;
  git_commit: string;
  git_commit_short: string;
  creation_timestamp: string;
  aggregate_quality: number | null;
  experiment_count: number;
  total_traces: number;
}

export interface AgentVersionDetail extends AgentVersionSummary {
  git_repo_url: string;
  experiment_results: ExperimentResult[];
  config: AgentConfig;
}

export interface AgentVersionsResponse {
  agents: AgentVersionSummary[];
}
