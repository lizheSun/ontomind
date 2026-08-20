/** Ontology API */
import api from './api';
import type {
  GraphData,
  LinkType,
  ObjectType,
  Ontology,
  OntologyBuildJob,
  OntologyCQ,
  OntologyMapping,
  OntologyMetric,
  OntologyProperty,
  OntologyVersion,
  ReviewItem,
} from '../types/ontology';

const B = '/ontology';

function errMsg(e: unknown, fallback: string): string {
  const err = e as { response?: { data?: { detail?: { message?: string } | string } }; message?: string };
  const d = err.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (d && typeof d === 'object' && d.message) return String(d.message);
  return err.message || fallback;
}

export { errMsg as ontologyErrMsg };

export async function listOntologies(): Promise<Ontology[]> {
  const res = await api.get(`${B}/ontologies`);
  return res.data as Ontology[];
}

export async function createOntology(data: {
  name: string;
  slug: string;
  description?: string;
  domain?: string;
}): Promise<Ontology> {
  const res = await api.post(`${B}/ontologies`, data);
  return res.data as Ontology;
}

export async function createBuildJob(
  oid: number,
  data: {
    mode?: 'rules' | 'llm' | 'hybrid';
    scope?: { source_id?: number; database?: string; tables?: string[] };
    batch_size?: number;
    reuse_domain_fragment?: string | null;
  },
): Promise<OntologyBuildJob> {
  const res = await api.post(`${B}/ontologies/${oid}/build-jobs`, data);
  return res.data as OntologyBuildJob;
}

export async function getBuildJob(jobId: number): Promise<OntologyBuildJob> {
  const res = await api.get(`${B}/build-jobs/${jobId}`);
  return res.data as OntologyBuildJob;
}

export async function listObjectTypes(oid: number, status?: string): Promise<ObjectType[]> {
  const res = await api.get(`${B}/ontologies/${oid}/object-types`, { params: { status } });
  return res.data as ObjectType[];
}

export async function listProperties(otId: number): Promise<OntologyProperty[]> {
  const res = await api.get(`${B}/object-types/${otId}/properties`);
  return res.data as OntologyProperty[];
}

export async function listLinkTypes(oid: number, status?: string): Promise<LinkType[]> {
  const res = await api.get(`${B}/ontologies/${oid}/link-types`, { params: { status } });
  return res.data as LinkType[];
}

export async function listMappings(oid: number, status?: string): Promise<OntologyMapping[]> {
  const res = await api.get(`${B}/ontologies/${oid}/mappings`, { params: { status } });
  return res.data as OntologyMapping[];
}

export async function listMetrics(oid: number): Promise<OntologyMetric[]> {
  const res = await api.get(`${B}/ontologies/${oid}/metrics`);
  return res.data as OntologyMetric[];
}

export async function inferRelations(
  oid: number,
  scope: { source_id?: number; database?: string; tables?: string[] },
): Promise<unknown> {
  const res = await api.post(`${B}/ontologies/${oid}/infer-relations`, { scope });
  return res.data;
}

export async function getOntologyGraph(
  oid: number,
  params?: { focus_key?: string; depth?: number },
): Promise<GraphData> {
  const res = await api.get(`${B}/ontologies/${oid}/graph`, { params });
  return res.data as GraphData;
}

export async function publishOntology(oid: number, change_note?: string): Promise<OntologyVersion> {
  const res = await api.post(`${B}/ontologies/${oid}/publish`, { change_note });
  return res.data as OntologyVersion;
}

export async function listVersions(oid: number): Promise<OntologyVersion[]> {
  const res = await api.get(`${B}/ontologies/${oid}/versions`);
  return res.data as OntologyVersion[];
}

export async function rollbackOntology(oid: number, version: number): Promise<OntologyVersion> {
  const res = await api.post(`${B}/ontologies/${oid}/rollback`, { version });
  return res.data as OntologyVersion;
}

export async function listCQs(oid: number): Promise<OntologyCQ[]> {
  const res = await api.get(`${B}/ontologies/${oid}/cqs`);
  return res.data as OntologyCQ[];
}

export async function generateCQs(oid: number, mode?: string): Promise<OntologyCQ[]> {
  const res = await api.post(`${B}/ontologies/${oid}/cqs/generate`, null, {
    params: { mode: mode || 'rules' },
  });
  return res.data as OntologyCQ[];
}

export async function verifyAllCQs(oid: number): Promise<{ pass_rate?: number; [k: string]: unknown }> {
  const res = await api.post(`${B}/ontologies/${oid}/cqs/verify-all`, {});
  return res.data as { pass_rate?: number };
}

export async function exportOntology(oid: number, fmt: 'json' | 'jsonld' | 'turtle'): Promise<string> {
  const res = await api.get(`${B}/ontologies/${oid}/export`, { params: { fmt }, responseType: 'text' });
  return typeof res.data === 'string' ? res.data : JSON.stringify(res.data);
}

export async function reviewOntologyElements(
  oid: number,
  data: {
    items?: ReviewItem[];
    accept_all_drafts?: boolean;
    reject_all_drafts?: boolean;
  },
): Promise<{ updated?: number }> {
  const res = await api.post(`${B}/ontologies/${oid}/review`, data);
  return res.data as { updated?: number };
}
