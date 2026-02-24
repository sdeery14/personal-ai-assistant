/** TypeScript interfaces for Eval Dashboard API responses. */

export interface TrendPoint {
  runId: string;
  timestamp: string;
  evalType: string;
  passRate: number;
  averageScore: number;
  totalCases: number;
  errorCases: number;
  promptVersions: Record<string, string>;
  evalStatus: string;
}

export interface PromptChange {
  timestamp: string;
  runId: string;
  promptName: string;
  fromVersion: string;
  toVersion: string;
}

export interface TrendSummary {
  evalType: string;
  latestPassRate: number;
  trendDirection: string;
  runCount: number;
  points: TrendPoint[];
  promptChanges: PromptChange[];
}

export interface TrendsResponse {
  summaries: TrendSummary[];
}

export interface RegressionReport {
  evalType: string;
  baselineRunId: string;
  currentRunId: string;
  baselinePassRate: number;
  currentPassRate: number;
  deltaPp: number;
  threshold: number;
  verdict: string;
  changedPrompts: PromptChange[];
  baselineTimestamp: string;
  currentTimestamp: string;
}

export interface RegressionsResponse {
  reports: RegressionReport[];
  hasRegressions: boolean;
}

export interface PromptListItem {
  name: string;
  currentVersion: number;
}

export interface PromptsResponse {
  prompts: PromptListItem[];
}

export interface PromotionEvalCheck {
  evalType: string;
  passRate: number;
  threshold: number;
  passed: boolean;
  runId: string;
}

export interface PromotionGateResult {
  allowed: boolean;
  promptName: string;
  fromAlias: string;
  toAlias: string;
  version: number;
  evalResults: PromotionEvalCheck[];
  blockingEvals: string[];
  justifyingRunIds: string[];
}

export interface AuditRecord {
  action: string;
  promptName: string;
  fromVersion: number;
  toVersion: number;
  alias: string;
  timestamp: string;
  actor: string;
  reason: string;
}

export interface EvalRunResult {
  datasetPath: string;
  exitCode: number;
  passed: boolean;
}

export interface EvalRunStatus {
  runId: string;
  suite: string;
  status: string;
  total: number;
  completed: number;
  results: EvalRunResult[];
  regressionReports: RegressionReport[] | null;
  startedAt: string;
  finishedAt: string | null;
}

export interface RollbackInfo {
  promptName: string;
  currentVersion: number;
  previousVersion: number | null;
  alias: string;
}
