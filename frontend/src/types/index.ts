/** Common type definitions for the OntoMind platform. */

export interface DataSource {
  id: number;
  name: string;
  source_type: string;
  status: 'active' | 'inactive' | 'error';
  description?: string;
  created_at: string;
}

export interface OntologyEntity {
  id: number;
  name: string;
  entity_type: string;
  properties: Record<string, any>;
  confidence: number;
}

export interface Strategy {
  id: number;
  name: string;
  strategy_type: string;
  status: 'draft' | 'testing' | 'active' | 'archived';
  version: string;
  priority: number;
}

export interface MLModel {
  id: number;
  name: string;
  model_type: string;
  framework: string;
  metrics: Record<string, number>;
  status: string;
}

export interface ChartConfig {
  id: number;
  title: string;
  chart_type: 'line' | 'bar' | 'pie' | 'scatter';
  config: Record<string, any>;
}
