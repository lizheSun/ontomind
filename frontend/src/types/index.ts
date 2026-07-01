/** Common type definitions for the OntoMind platform. */

// ===== 资源管理 =====

export interface Instance {
  id: number;
  name: string;
  host: string;
  port: number;
  instance_type: 'physical' | 'docker' | 'k8s_pod';
  protocol: 'ssh' | 'docker_api';
  credential?: Record<string, any>;
  os?: string;
  cpu_cores?: number;
  memory_mb?: number;
  disk_gb?: number;
  labels?: Record<string, any>;
  status: 'online' | 'offline' | 'maintenance';
  last_heartbeat?: string;
  description?: string;
  created_at: string;
  updated_at?: string;
}

export interface Agent {
  id: number;
  name: string;
  agent_type: 'openclaw' | 'opencode' | 'harness' | 'custom';
  version: string;
  runtime: 'docker' | 'python' | 'node' | 'binary';
  docker_image?: string;
  entrypoint?: string;
  env_template?: Record<string, any>;
  config_template?: string;
  ports?: number[];
  volume_mounts?: Record<string, any>;
  resource_limit?: Record<string, any>;
  skill_ids?: number[];
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Skill {
  id: number;
  name: string;
  skill_type: 'docker' | 'mcp' | 'script' | 'api';
  docker_image?: string;
  entrypoint?: string;
  install_cmd?: string;
  parameters_schema?: Record<string, any>;
  output_schema?: Record<string, any>;
  env_vars?: Record<string, any>;
  description?: string;
  tags?: string[];
  icon?: string;
  is_installed: boolean;
  installed_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface MCPConfig {
  id: number;
  name: string;
  mcp_type: 'sse' | 'stdio' | 'http';
  url?: string;
  command?: string;
  args?: string[];
  env_vars?: Record<string, any>;
  headers?: Record<string, any>;
  auto_discovery_url?: string;
  auto_discovery_enabled: boolean;
  tools_manifest?: Record<string, any>;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AgentRun {
  id: number;
  agent_id?: number;
  instance_id?: number;
  run_name: string;
  status: 'initializing' | 'running' | 'error' | 'stopped';
  container_id?: string;
  pid?: number;
  config_override?: Record<string, any>;
  env_override?: Record<string, any>;
  started_at?: string;
  stopped_at?: string;
  exit_code?: number;
  error_message?: string;
  created_at: string;
  updated_at?: string;
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
}

// ===== 感知层 =====

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
