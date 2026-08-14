/** Skill 平台 API 服务 */
import api from './api';
import type {
  SkillFullResponse,
  SkillListItem,
  SkillMetaPayload,
  SkillParamResponse,
  SkillValidation,
  SkillVersionResponse,
  SkillAuditResponse,
  SkillExportResponse,
  ParamDebugResult
} from '../types/skillPlatform';

const B = '/skill-platform';

export async function listSkills(params?: {
  keyword?: string;
  kind?: string;
  lifecycle?: string;
  risk_level?: string;
  biz_line?: string;
}): Promise<SkillListItem[]> {
  const res = await api.get(`${B}/skills`, { params });
  return res.data as SkillListItem[];
}

export async function createSkill(data: {
  name: string;
  description: string;
  display_name?: string;
  category?: string;
  license?: string;
  body?: string;
  meta?: SkillMetaPayload;
}): Promise<SkillFullResponse> {
  const res = await api.post(`${B}/skills`, data);
  return res.data as SkillFullResponse;
}

export async function getSkill(id: number): Promise<SkillFullResponse> {
  const res = await api.get(`${B}/skills/${id}`);
  return res.data as SkillFullResponse;
}

export async function updateSkill(id: number, data: Record<string, unknown>): Promise<SkillFullResponse> {
  const res = await api.put(`${B}/skills/${id}`, data);
  return res.data as SkillFullResponse;
}

export async function deleteSkill(id: number): Promise<void> {
  await api.delete(`${B}/skills/${id}`);
}

export async function validateSkill(payload: Record<string, unknown>): Promise<SkillValidation> {
  const res = await api.post(`${B}/skills/validate`, payload);
  return res.data as SkillValidation;
}

export async function changeLifecycle(id: number, to: string, note?: string): Promise<SkillMetaPayload> {
  const res = await api.post(`${B}/skills/${id}/lifecycle`, { to, note });
  return res.data as SkillMetaPayload;
}

export async function updateParams(
  id: number, direction: 'in' | 'out', params: Record<string, unknown>[],
): Promise<SkillParamResponse[]> {
  const res = await api.put(`${B}/skills/${id}/params`, { direction, params });
  return res.data as SkillParamResponse[];
}

export async function debugParams(id: number, sample_json: Record<string, unknown>): Promise<ParamDebugResult> {
  const res = await api.post(`${B}/skills/${id}/params/debug`, { sample_json });
  return res.data as ParamDebugResult;
}

export async function exportSkill(id: number, scope = 'project', include_manifest = true): Promise<SkillExportResponse> {
  const res = await api.post(`${B}/skills/${id}/export`, { scope, include_manifest });
  return res.data as SkillExportResponse;
}

export async function createVersion(id: number, change_note?: string, canary?: Record<string, unknown>): Promise<SkillVersionResponse> {
  const res = await api.post(`${B}/skills/${id}/versions`, { change_note, canary });
  return res.data as SkillVersionResponse;
}

export async function listVersions(id: number): Promise<SkillVersionResponse[]> {
  const res = await api.get(`${B}/skills/${id}/versions`);
  return res.data as SkillVersionResponse[];
}

export async function rollbackSkill(id: number, version: number): Promise<SkillFullResponse> {
  const res = await api.post(`${B}/skills/${id}/rollback`, { version });
  return res.data as SkillFullResponse;
}

export async function cloneSkill(id: number, new_name: string): Promise<SkillFullResponse> {
  const res = await api.post(`${B}/skills/${id}/clone`, { new_name });
  return res.data as SkillFullResponse;
}

export async function listAudit(id: number): Promise<SkillAuditResponse[]> {
  const res = await api.get(`${B}/skills/${id}/audit`);
  return res.data as SkillAuditResponse[];
}

export const skillPlatformService = {
  listSkills, createSkill, getSkill, updateSkill, deleteSkill, validateSkill,
  changeLifecycle, updateParams, debugParams, exportSkill,
  createVersion, listVersions, rollbackSkill, cloneSkill, listAudit,
};