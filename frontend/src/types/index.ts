/** Common type definitions for the OntoMind platform. */

export interface DataSource {
  id: number;
  name: string;
  source_type: string;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  database?: string;
  charset?: string;
  description?: string;
  status: 'active' | 'inactive' | 'error';
  extra_params?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface TestConnectionResult {
  success: boolean;
  message: string;
  details?: string;
  diagnosis?: string;
}

export interface AutoConfigureResult {
  datasource: DataSource;
  parsed_config: Record<string, any>;
  test_result: TestConnectionResult;
}

export interface ParsedConfigResult {
  parsed: Record<string, any>;
  raw_text: string;
  model_used?: string;
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
