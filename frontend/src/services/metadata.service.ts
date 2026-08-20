/** Metadata API */
import api from './api';
import type {
  AnnotateStats,
  Annotation,
  ColumnWorkspaceItem,
  DatabaseBrief,
  GlossaryTerm,
  LlmSetting,
  LlmTestResult,
  MetaColumn,
  MetaScanJob,
  MetaStandard,
  MetaTable,
} from '../types/metadata';

const B = '/metadata';

export async function createMetaScan(data: {
  source_id: number;
  database: string;
  tables?: string[];
  with_profile?: boolean;
}): Promise<MetaScanJob> {
  const res = await api.post(`${B}/scans`, data);
  return res.data as MetaScanJob;
}

export async function listMetaJobs(params?: {
  source_id?: number;
  database?: string;
  job_kind?: string;
  status?: string;
  limit?: number;
}): Promise<MetaScanJob[]> {
  const res = await api.get(`${B}/jobs`, { params });
  return res.data as MetaScanJob[];
}

export async function getMetaJob(jobId: number): Promise<MetaScanJob> {
  const res = await api.get(`${B}/jobs/${jobId}`);
  return res.data as MetaScanJob;
}

export async function getMetaScan(jobId: number): Promise<MetaScanJob> {
  return getMetaJob(jobId);
}

export async function listMetaTables(params: {
  source_id: number;
  database?: string;
  keyword?: string;
}): Promise<MetaTable[]> {
  const res = await api.get(`${B}/tables`, { params });
  return res.data as MetaTable[];
}

export async function getMetaTable(tableId: number): Promise<MetaTable & { columns?: MetaColumn[] }> {
  const res = await api.get(`${B}/tables/${tableId}`);
  return res.data as MetaTable & { columns?: MetaColumn[] };
}

export async function updateMetaColumn(
  columnId: number,
  data: { biz_name?: string; biz_description?: string; semantic_type?: string; pii_level?: string },
): Promise<MetaColumn> {
  const res = await api.put(`${B}/columns/${columnId}`, data);
  return res.data as MetaColumn;
}

export async function listWorkspaceColumns(params: {
  source_id: number;
  database: string;
  table_name?: string;
  column_name?: string;
  security_level?: string;
  standard_id?: number;
  bind_status?: string;
  bound?: boolean;
  limit?: number;
  offset?: number;
}): Promise<ColumnWorkspaceItem[]> {
  const res = await api.get(`${B}/workspace/columns`, { params });
  return res.data as ColumnWorkspaceItem[];
}

export async function listStandards(params?: { keyword?: string; status?: string }): Promise<MetaStandard[]> {
  const res = await api.get(`${B}/standards`, { params });
  return res.data as MetaStandard[];
}

export async function createStandard(data: Partial<MetaStandard> & { code: string; name: string }): Promise<MetaStandard> {
  const res = await api.post(`${B}/standards`, {
    code: data.code,
    name: data.name,
    aliases: data.aliases_json,
    description: data.description,
    semantic_type: data.semantic_type,
    data_type_expect: data.data_type_expect,
    length_rule: data.length_rule_json,
    security_level: data.security_level || 'L0',
    quality_rule: data.quality_rule_json,
    mask_rule: data.mask_rule,
    domain: data.domain,
    status: data.status || 'published',
  });
  return res.data as MetaStandard;
}

export async function updateStandard(id: number, data: Record<string, unknown>): Promise<MetaStandard> {
  const res = await api.put(`${B}/standards/${id}`, data);
  return res.data as MetaStandard;
}

export async function deleteStandard(id: number): Promise<void> {
  await api.delete(`${B}/standards/${id}`);
}

export async function bindColumnStandard(
  columnId: number,
  data: { standard_id: number; security_level_override?: string },
): Promise<ColumnWorkspaceItem> {
  const res = await api.post(`${B}/columns/${columnId}/bind-standard`, {
    ...data,
    status: 'accepted',
    source: 'human',
  });
  return res.data as ColumnWorkspaceItem;
}

export async function batchBindStandard(data: {
  column_ids: number[];
  standard_id: number;
  security_level_override?: string;
}): Promise<ColumnWorkspaceItem[]> {
  const res = await api.post(`${B}/columns/batch-bind-standard`, data);
  return res.data as ColumnWorkspaceItem[];
}

export async function unbindColumnStandard(columnId: number): Promise<void> {
  await api.delete(`${B}/columns/${columnId}/bind-standard`);
}

export async function getDatabaseBrief(sourceId: number, database: string): Promise<DatabaseBrief | null> {
  const res = await api.get(`${B}/briefs`, { params: { source_id: sourceId, database } });
  return (res.data as DatabaseBrief) || null;
}

export async function createDatabaseBrief(data: {
  source_id: number;
  database: string;
  mode?: 'rules' | 'llm';
}): Promise<MetaScanJob> {
  const res = await api.post(`${B}/briefs`, data);
  return res.data as MetaScanJob;
}

export async function createAnnotateJob(data: {
  source_id: number;
  database: string;
  tables?: string[];
  mode?: 'rules' | 'llm' | 'hybrid';
  label_kinds?: string[];
}): Promise<MetaScanJob> {
  const res = await api.post(`${B}/annotate-jobs`, data);
  return res.data as MetaScanJob;
}

export async function getAnnotateJob(jobId: number): Promise<MetaScanJob> {
  const res = await api.get(`${B}/annotate-jobs/${jobId}`);
  return res.data as MetaScanJob;
}

export async function listAnnotations(params?: {
  status?: string;
  label_kind?: string;
  source?: string;
}): Promise<Annotation[]> {
  const res = await api.get(`${B}/annotations`, { params });
  return res.data as Annotation[];
}

export async function reviewAnnotation(
  id: number,
  action: 'accept' | 'reject',
  value_override?: string,
): Promise<Annotation> {
  const res = await api.post(`${B}/annotations/${id}/review`, { action, value_override });
  return res.data as Annotation;
}

export async function batchReviewAnnotations(
  ann_ids: number[],
  action: 'accept' | 'reject',
): Promise<Annotation[]> {
  const res = await api.post(`${B}/annotations/batch-review`, { ann_ids, action });
  return res.data as Annotation[];
}

export async function getAnnotateStats(sourceId: number, database: string): Promise<AnnotateStats> {
  const res = await api.get(`${B}/stats`, { params: { source_id: sourceId, database } });
  return res.data as AnnotateStats;
}

export async function listGlossary(): Promise<GlossaryTerm[]> {
  const res = await api.get(`${B}/glossary`);
  return res.data as GlossaryTerm[];
}

export async function extractGlossary(data: {
  doc_ids?: number[];
  mode?: 'rules' | 'llm';
}): Promise<GlossaryTerm[]> {
  const res = await api.post(`${B}/glossary/extract`, data);
  return res.data as GlossaryTerm[];
}

export interface LlmSettingPayload {
  name?: string;
  base_url?: string;
  model?: string;
  api_key?: string;
  timeout?: number;
  max_concurrency?: number;
  enabled?: boolean;
  is_default?: boolean;
}

export async function listLlmSettings(): Promise<LlmSetting[]> {
  const res = await api.get(`${B}/llm-settings`);
  return res.data as LlmSetting[];
}

export async function getActiveLlmSetting(): Promise<LlmSetting> {
  const res = await api.get(`${B}/llm-settings/active`);
  return res.data as LlmSetting;
}

export async function createLlmSetting(data: LlmSettingPayload & { base_url: string; model: string; api_key: string }): Promise<LlmSetting> {
  const res = await api.post(`${B}/llm-settings`, data);
  return res.data as LlmSetting;
}

export async function updateLlmSetting(id: number, data: LlmSettingPayload): Promise<LlmSetting> {
  const res = await api.put(`${B}/llm-settings/${id}`, data);
  return res.data as LlmSetting;
}

export async function deleteLlmSetting(id: number): Promise<void> {
  await api.delete(`${B}/llm-settings/${id}`);
}

export async function applyLlmSetting(id: number): Promise<LlmSetting> {
  const res = await api.post(`${B}/llm-settings/${id}/apply`);
  return res.data as LlmSetting;
}

export async function testSavedLlmSetting(id: number): Promise<LlmTestResult> {
  const res = await api.post(`${B}/llm-settings/${id}/test`);
  return res.data as LlmTestResult;
}

export async function testLlmSettings(data: { base_url: string; model: string; api_key: string; timeout?: number }): Promise<LlmTestResult> {
  const res = await api.post(`${B}/llm-settings/test`, data);
  return res.data as LlmTestResult;
}
