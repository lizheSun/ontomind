/** Metadata + standards types */
export type ScanStatus = 'pending' | 'running' | 'succeeded' | 'failed';

export interface MetaScanJob {
  id: number;
  source_id: number;
  database: string;
  job_kind: string;
  status: ScanStatus | string;
  progress?: number | null;
  with_profile?: boolean;
  mode?: string | null;
  stats_json?: Record<string, unknown> | null;
  error_detail?: string | null;
  duration_ms?: number | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
}

export interface MetaTable {
  id: number;
  source_id: number;
  database: string;
  table_name: string;
  table_type?: string | null;
  table_comment?: string | null;
  row_count?: number | null;
  biz_name?: string | null;
  biz_description?: string | null;
  domain?: string | null;
  column_count?: number | null;
}

export interface MetaColumn {
  id: number;
  table_id: number;
  column_name: string;
  data_type?: string | null;
  column_type?: string | null;
  nullable?: boolean;
  column_key?: string | null;
  column_comment?: string | null;
  biz_name?: string | null;
  biz_description?: string | null;
  semantic_type?: string | null;
  pii_level?: string | null;
  profile_json?: Record<string, unknown> | null;
}

export interface MetaStandard {
  id: number;
  code: string;
  name: string;
  aliases_json?: string[] | null;
  description?: string | null;
  semantic_type?: string | null;
  data_type_expect?: string | null;
  length_rule_json?: Record<string, unknown> | null;
  security_level: string;
  quality_rule_json?: Record<string, unknown> | null;
  mask_rule?: string | null;
  domain?: string | null;
  status: string;
  current_version: number;
  bound_column_count?: number;
}

export interface ColumnWorkspaceItem {
  id: number;
  table_id: number;
  table_name: string;
  column_name: string;
  data_type?: string | null;
  column_type?: string | null;
  nullable?: boolean;
  column_key?: string | null;
  column_comment?: string | null;
  biz_name?: string | null;
  pii_level?: string | null;
  semantic_type?: string | null;
  bind_id?: number | null;
  standard_id?: number | null;
  standard_code?: string | null;
  standard_name?: string | null;
  standard_version?: number | null;
  bind_status?: string | null;
  effective_security_level?: string | null;
  length_rule_json?: Record<string, unknown> | null;
  quality_rule_json?: Record<string, unknown> | null;
}

export interface DatabaseBrief {
  id: number;
  source_id: number;
  database: string;
  mode: string;
  content_md?: string | null;
  stats_json?: Record<string, unknown> | null;
  job_id?: number | null;
}

export interface LlmSetting {
  id: number;
  name: string;
  base_url: string;
  model: string;
  api_key_masked?: string | null;
  has_api_key: boolean;
  timeout: number;
  max_concurrency: number;
  enabled: boolean;
  is_default: boolean;
  source: 'db' | 'env' | 'none';
  configured: boolean;
}

export interface LlmTestResult {
  ok: boolean;
  reply?: string;
  latency_ms?: number;
}

export interface Annotation {
  id: number;
  target_type: string;
  target_id: number;
  label_kind: string;
  label_value?: string | null;
  confidence: number;
  source: string;
  status: string;
  evidence_json?: Record<string, unknown> | null;
}

export interface GlossaryTerm {
  id: number;
  name: string;
  aliases?: string[] | null;
  definition?: string | null;
  domain?: string | null;
  source_type?: string | null;
  confidence?: number | null;
}

export interface AnnotateStats {
  table_biz_name_coverage?: number;
  column_biz_name_coverage?: number;
  accepted_count?: number;
  suggested_count?: number;
  rejected_count?: number;
  standard_coverage?: number;
  accepted?: number;
  suggested?: number;
  [key: string]: unknown;
}
