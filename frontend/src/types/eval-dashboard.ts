/** TypeScript interfaces for Eval Dashboard API responses. */

export interface TrendPoint {
  run_id: string;
  timestamp: string;
  eval_type: string;
  pass_rate: number;
  average_score: number;
  total_cases: number;
  error_cases: number;
  prompt_versions: Record<string, string>;
  eval_status: string;
}

export interface PromptChange {
  timestamp: string;
  run_id: string;
  prompt_name: string;
  from_version: string;
  to_version: string;
}

export interface TrendSummary {
  eval_type: string;
  latest_pass_rate: number;
  trend_direction: string;
  run_count: number;
  points: TrendPoint[];
  prompt_changes: PromptChange[];
}

export interface TrendsResponse {
  summaries: TrendSummary[];
}

export interface RegressionReport {
  eval_type: string;
  baseline_run_id: string;
  current_run_id: string;
  baseline_pass_rate: number;
  current_pass_rate: number;
  delta_pp: number;
  threshold: number;
  verdict: string;
  changed_prompts: PromptChange[];
  baseline_timestamp: string;
  current_timestamp: string;
}

export interface RegressionsResponse {
  reports: RegressionReport[];
  has_regressions: boolean;
}

export interface PromptListItem {
  name: string;
  current_version: number;
}

export interface PromptsResponse {
  prompts: PromptListItem[];
}

export interface PromotionEvalCheck {
  eval_type: string;
  pass_rate: number;
  threshold: number;
  passed: boolean;
  run_id: string;
}

export interface PromotionGateResult {
  allowed: boolean;
  prompt_name: string;
  from_alias: string;
  to_alias: string;
  version: number;
  eval_results: PromotionEvalCheck[];
  blocking_evals: string[];
  justifying_run_ids: string[];
}

export interface AuditRecord {
  action: string;
  prompt_name: string;
  from_version: number;
  to_version: number;
  alias: string;
  timestamp: string;
  actor: string;
  reason: string;
}

export interface EvalRunResult {
  dataset_path: string;
  exit_code: number;
  passed: boolean;
}

export interface EvalRunStatus {
  run_id: string;
  suite: string;
  status: string;
  total: number;
  completed: number;
  results: EvalRunResult[];
  regression_reports: RegressionReport[] | null;
  started_at: string;
  finished_at: string | null;
}

export interface RollbackInfo {
  prompt_name: string;
  current_version: number;
  previous_version: number | null;
  alias: string;
}

export interface RunCaseResult {
  case_id: string;
  score: number | null;
  duration_ms: number | null;
  error: string | null;
  user_prompt: string;
  assistant_response: string;
  justification: string | null;
  rating: string | null;
  extra: Record<string, unknown>;
}

export interface RunDetail {
  run_id: string;
  eval_type: string;
  timestamp: string;
  params: Record<string, string>;
  metrics: Record<string, number>;
  cases: RunCaseResult[];
}
