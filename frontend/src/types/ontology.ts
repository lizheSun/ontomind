/** Ontology API types */

export interface Ontology {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  domain?: string | null;
  current_version: number;
}

export interface OntologyBuildJob {
  id: number;
  ontology_id: number;
  status: string;
  phase?: string | null;
  mode?: string | null;
  progress?: number | null;
  error_detail?: string | null;
  scope_json?: Record<string, unknown> | null;
  delta_json?: Record<string, unknown> | null;
  duration_ms?: number | null;
}

export interface ObjectType {
  id: number;
  ontology_id: number;
  key: string;
  display_name?: string | null;
  definition?: string | null;
  parent_key?: string | null;
  confidence: number;
  source: string;
  status: string;
}

export interface OntologyProperty {
  id: number;
  ontology_id: number;
  object_type_id: number;
  key: string;
  display_name?: string | null;
  data_type?: string | null;
  confidence: number;
  source: string;
  status: string;
}

export interface LinkType {
  id: number;
  ontology_id: number;
  key: string;
  display_name?: string | null;
  from_key: string;
  to_key: string;
  cardinality?: string | null;
  confidence: number;
  source: string;
  status: string;
}

export interface OntologyMapping {
  id: number;
  ontology_id: number;
  element_type: string;
  element_key: string;
  source_id?: number | null;
  database?: string | null;
  table_name?: string | null;
  column_name?: string | null;
  confidence: number;
  source: string;
  status: string;
}

export interface OntologyMetric {
  id: number;
  ontology_id: number;
  key: string;
  display_name: string;
  definition?: string | null;
  sql_expr?: string | null;
  unit?: string | null;
  confidence: number;
  source: string;
  status: string;
}

export interface OntologyVersion {
  id: number;
  ontology_id: number;
  version: number;
  change_note?: string | null;
  diff_json?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface GraphData {
  nodes: Array<{
    id: string;
    key: string;
    label: string;
    parent?: string | null;
    confidence?: number;
    status?: string;
    table_count?: number;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
    cardinality?: string;
    confidence?: number;
    status?: string;
  }>;
}

export interface OntologyCQ {
  id: number;
  ontology_id: number;
  question: string;
  category?: string | null;
  verify_status: string;
  verify_note?: string | null;
}

export type ReviewElementType = 'object_type' | 'property' | 'link_type' | 'mapping' | 'metric';

export interface ReviewItem {
  element_type: ReviewElementType;
  element_id: number;
  action: 'accept' | 'reject';
}
