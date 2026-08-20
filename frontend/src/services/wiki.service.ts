/** Wiki API */
import api from './api';
import type {
  WikiDocument,
  WikiDocumentListItem,
  WikiDocumentVersion,
  WikiImportPayload,
  WikiSpace,
} from '../types/wiki';

const B = '/wiki';

export async function listWikiSpaces(): Promise<WikiSpace[]> {
  const res = await api.get(`${B}/spaces`);
  return res.data as WikiSpace[];
}

export async function createWikiSpace(data: {
  name: string;
  slug: string;
  description?: string;
}): Promise<WikiSpace> {
  const res = await api.post(`${B}/spaces`, data);
  return res.data as WikiSpace;
}

export async function listWikiDocuments(params?: {
  space_id?: number;
  keyword?: string;
  tag?: string;
  status?: string;
}): Promise<WikiDocumentListItem[]> {
  const res = await api.get(`${B}/documents`, { params });
  return res.data as WikiDocumentListItem[];
}

export async function getWikiDocument(id: number): Promise<WikiDocument> {
  const res = await api.get(`${B}/documents/${id}`);
  return res.data as WikiDocument;
}

export async function createWikiDocument(data: Record<string, unknown>): Promise<WikiDocument> {
  const res = await api.post(`${B}/documents`, data);
  return res.data as WikiDocument;
}

export async function updateWikiDocument(
  id: number,
  data: Record<string, unknown>,
): Promise<WikiDocument> {
  const res = await api.put(`${B}/documents/${id}`, data);
  return res.data as WikiDocument;
}

export async function deleteWikiDocument(id: number): Promise<void> {
  await api.delete(`${B}/documents/${id}`);
}

export async function listWikiVersions(id: number): Promise<WikiDocumentVersion[]> {
  const res = await api.get(`${B}/documents/${id}/versions`);
  return res.data as WikiDocumentVersion[];
}

export async function rollbackWikiDocument(id: number, version: number): Promise<WikiDocument> {
  const res = await api.post(`${B}/documents/${id}/rollback`, { version });
  return res.data as WikiDocument;
}

export async function importWikiDocument(data: WikiImportPayload): Promise<WikiDocument> {
  const res = await api.post(`${B}/import`, data);
  return res.data as WikiDocument;
}

export async function fetchWikiUrl(url: string): Promise<{ url: string; html: string }> {
  const res = await api.post(`${B}/fetch-url`, { url });
  return res.data as { url: string; html: string };
}
