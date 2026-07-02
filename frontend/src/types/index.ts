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

export interface DiscoveredAgent {
  agent_type: 'openclaw' | 'opencode' | 'harness' | 'custom';
  label: string;
  icon: string;
  port: number;
  host: string;
  health_url?: string;
  is_healthy: boolean;
  version?: string;
  process_name?: string;
  error?: string;
}

export interface AgentScanResult {
  instance_id: number;
  host: string;
  agents: DiscoveredAgent[];
  total_ports_scanned: number;
  errors?: string[];
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

// ===== 项目管理 =====

export interface Project {
  id: number;
  name: string;
  key: string;
  description?: string;
  status: 'active' | 'archived';
  icon?: string;
  color?: string;
  extra?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface Requirement {
  id: number;
  project_id: number;
  title: string;
  req_type: 'feature' | 'bug' | 'improvement' | 'performance';
  priority: 'P0' | 'P1' | 'P2' | 'P3';
  status: 'pending_review' | 'passed' | 'rejected' | 'in_progress' | 'done';
  description?: string;
  acceptance_criteria?: string;
  impact_scope?: string;
  related_modules?: string[];
  score_clarity?: number;
  score_feasibility?: number;
  score_value?: number;
  score_total?: number;
  review_comment?: string;
  review_agent_id?: number;
  is_decomposed: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Plan {
  id: number;
  project_id: number;
  name: string;
  plan_type: 'sprint' | 'release' | 'milestone';
  goal?: string;
  start_date?: string;
  end_date?: string;
  status: 'planned' | 'active' | 'completed' | 'cancelled';
  created_at: string;
  updated_at?: string;
}

export interface Task {
  id: number;
  project_id: number;
  plan_id?: number;
  requirement_id?: number;
  title: string;
  description?: string;
  status: 'todo' | 'in_progress' | 'review' | 'done';
  priority: 'P0' | 'P1' | 'P2' | 'P3';
  assignee_agent_type?: string;
  assignee_agent_id?: number;
  estimated_hours?: number;
  actual_hours?: number;
  position: number;
  created_at: string;
  updated_at?: string;
}

export interface KanbanData {
  todo: Task[];
  in_progress: Task[];
  review: Task[];
  done: Task[];
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
